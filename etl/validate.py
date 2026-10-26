"""Data-quality checks. Input: dict of DataFrames shaped like the DB tables:
sales, products, customers (required); inventory, returns (optional)."""

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

FRESHNESS_DAYS = 7
MAX_SNAPSHOT_GAP_DAYS = 14

REQUIRED = {
    "sales": [
        "order_line_id",
        "order_id",
        "order_date_key",
        "product_key",
        "customer_key",
        "qty_ordered",
        "qty_shipped",
        "unit_price",
        "unit_cost",
        "discount_pct",
    ],
    "products": ["product_key", "sku"],
    "customers": ["customer_key"],
}
KEY_COLS = REQUIRED["sales"]


@dataclass
class Result:
    name: str
    severity: str
    passed: bool
    detail: str


CHECKS = []


def check(name, severity="Error"):
    def deco(fn):
        CHECKS.append((name, severity, fn))
        return fn

    return deco


def _dates(keys: pd.Series) -> pd.Series:
    return pd.to_datetime(
        keys.astype("Int64").astype(str), format="%Y%m%d", errors="coerce"
    )


def _count(mask, what):
    n = int(mask.sum())
    return n == 0, "ok" if n == 0 else f"{n:,} {what}"


# ---- the 15 checks -------------------------------------------------------
def required_columns(d):
    missing = {
        t: [c for c in cols if c not in d[t].columns]
        for t, cols in REQUIRED.items()
        if t in d
    }
    missing = {t: c for t, c in missing.items() if c}
    return (not missing), ("ok" if not missing else f"missing columns: {missing}")


@check("No duplicate order lines")
def dup_lines(d):
    return _count(
        d["sales"].duplicated(["order_id", "product_key"]),
        "duplicate (order, product) lines",
    )


@check("order_line_id is unique")
def unique_ids(d):
    return _count(
        d["sales"].order_line_id.duplicated(), "repeated order_line_id values"
    )


@check("No nulls in key/measure columns")
def no_nulls(d):
    return _count(d["sales"][KEY_COLS].isna().any(axis=1), "rows with nulls")


@check("Shipped quantity <= ordered quantity")
def shipped_le_ordered(d):
    s = d["sales"]
    return _count(s.qty_shipped > s.qty_ordered, "lines shipped more than ordered")


@check("Prices and costs are non-negative")
def non_negative(d):
    s = d["sales"]
    return _count(
        (s.unit_price < 0) | (s.unit_cost < 0), "lines with negative price/cost"
    )


@check("Discount between 0 and 1")
def discount_range(d):
    return _count(
        ~d["sales"].discount_pct.between(0, 1), "lines with discount outside 0-1"
    )


@check("Dates valid and not in the future")
def valid_dates(d):
    dt = _dates(d["sales"].order_date_key)
    bad = dt.isna() | (dt > pd.Timestamp.today()) | (dt < pd.Timestamp("2000-01-01"))
    return _count(bad, "lines with invalid/future dates")


@check("Every SKU exists in product master")
def sku_exists(d):
    return _count(
        ~d["sales"].product_key.isin(d["products"].product_key),
        "lines with unknown SKU",
    )


@check("Every customer exists in customer master")
def customer_exists(d):
    return _count(
        ~d["sales"].customer_key.isin(d["customers"].customer_key),
        "lines with unknown customer",
    )


@check("Returned qty <= shipped qty")
def returns_le_shipped(d):
    if "returns" not in d:
        return True, "skipped (no returns data)"
    m = d["returns"].merge(
        d["sales"][["order_line_id", "qty_shipped"]], on="order_line_id", how="left"
    )
    return _count(
        (m.qty_returned > m.qty_shipped) | m.qty_shipped.isna(),
        "returns exceeding shipped qty / orphan returns",
    )


@check("Unit price >= unit cost", severity="Warning")
def price_ge_cost(d):
    s = d["sales"]
    return _count(s.unit_price < s.unit_cost, "negative-margin lines")


@check("No extreme price outliers", severity="Warning")
def price_outliers(d):
    s = d["sales"]
    g = s.groupby("product_key").unit_price
    q1, q3 = (
        g.transform(lambda x: x.quantile(0.25)),
        g.transform(lambda x: x.quantile(0.75)),
    )
    iqr = q3 - q1
    return _count(
        (s.unit_price < q1 - 3 * iqr) | (s.unit_price > q3 + 3 * iqr),
        "price outliers (3xIQR per SKU)",
    )


@check("Inventory snapshots have no large gaps", severity="Warning")
def snapshot_gaps(d):
    if "inventory" not in d:
        return True, "skipped (no inventory data)"
    inv = (
        d["inventory"]
        .assign(dt=_dates(d["inventory"].snapshot_date_key))
        .sort_values(["product_key", "dt"])
    )
    gap = inv.groupby("product_key").dt.diff().dt.days.max()
    ok = pd.isna(gap) or gap <= MAX_SNAPSHOT_GAP_DAYS
    return bool(ok), "ok" if ok else f"largest gap is {int(gap)} days"


@check("Data is fresh", severity="Warning")
def freshness(d):
    latest = _dates(d["sales"].order_date_key).max()
    age = (pd.Timestamp.today().normalize() - latest).days
    return age <= FRESHNESS_DAYS, f"latest order is {age} days old"


# ---- runner ----------------------------------------------------------------
def run_all(d) -> list[Result]:
    ok, detail = required_columns(d)
    results = [Result("Required columns present", "Error", ok, detail)]
    if not ok:
        return results
    for name, sev, fn in CHECKS:
        try:
            ok, detail = fn(d)
        except Exception as e:  # noqa: BLE001 — isolate failures between checks
            ok, detail = False, f"check crashed: {e}"
        results.append(Result(name, sev, bool(ok), detail))
    return results


def has_errors(results) -> bool:
    return any(r.severity == "Error" and not r.passed for r in results)


if __name__ == "__main__":  # python -m etl.validate data/sample
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw")
    files = {
        "sales": "fact_sales",
        "products": "dim_product",
        "customers": "dim_customer",
        "inventory": "fact_inventory_snapshot",
        "returns": "fact_returns",
    }
    data = {
        k: pd.read_csv(src / f"{v}.csv")
        for k, v in files.items()
        if (src / f"{v}.csv").exists()
    }
    res = run_all(data)
    for r in res:
        print(
            f"[{'PASS' if r.passed else 'FAIL'}] {r.severity:7s} {r.name}: {r.detail}"
        )
    sys.exit(1 if has_errors(res) else 0)
