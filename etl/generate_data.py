"""Synthetic ERP-style data generator.

Usage:  python -m etl.generate_data --orders 120000 --out data/raw
Simplification: demand is generated independently of stock levels, so inventory
is simulated *from* demand rather than limiting it.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
CATEGORIES = {  # category: (subcategories, min_cost, max_cost)
    "Electronics": (["Mobiles", "Audio", "Accessories"], 400, 12000),
    "Home Decor": (["Wall Art", "Lighting", "Furnishing"], 150, 3000),
    "Kitchen": (["Cookware", "Appliances", "Storage"], 100, 4000),
    "Apparel": (["Men", "Women", "Kids"], 120, 1800),
    "Stationery": (["Paper", "Writing", "Office"], 10, 400),
}
DECLINING_CATEGORY = "Home Decor"
HIGH_RETURN_COUNT = 3
STOCKOUT_PRONE_SHARE = 0.06


def key(s: pd.Series) -> pd.Series:
    return s.dt.strftime("%Y%m%d").astype(int)


def build(n_orders: int, out: str) -> None:
    rng = np.random.default_rng(SEED)
    fake = Faker("en_IN")
    Faker.seed(SEED)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    end = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
    start = end - pd.Timedelta(days=729)           # ~2 years of history
    dates = pd.date_range(start, end, freq="D")
    s = pd.Series(dates)

    # ---------- dim_date ----------
    dim_date = pd.DataFrame({
        "date_key": key(s), "full_date": s.dt.strftime("%Y-%m-%d"),
        "year": s.dt.year, "quarter": s.dt.quarter, "month": s.dt.month,
        "month_name": s.dt.strftime("%b"),
        "week_of_year": s.dt.isocalendar().week.astype(int),
        "day_of_week": s.dt.dayofweek, "is_weekend": (s.dt.dayofweek >= 5).astype(int),
    })

    # ---------- dimensions ----------
    n_sup, n_prod, n_cust = 25, 400, 1500
    suppliers = pd.DataFrame({
        "supplier_key": range(1, n_sup + 1),
        "supplier_name": [fake.company() for _ in range(n_sup)],
        "country": rng.choice(["India", "China", "Vietnam", "Germany"], n_sup, p=[.6, .25, .1, .05]),
        "lead_time_days": rng.integers(5, 46, n_sup),
    })

    cats = rng.choice(list(CATEGORIES), n_prod)
    subs, cost = [], []
    for c in cats:
        sub_list, lo, hi = CATEGORIES[c]
        subs.append(rng.choice(sub_list))
        cost.append(round(rng.uniform(lo, hi), 2))
    cost = np.array(cost)
    products = pd.DataFrame({
        "product_key": range(1, n_prod + 1),
        "sku": [f"SKU-{i:04d}" for i in range(1, n_prod + 1)],
        "product_name": [f"{c} item {i}" for i, c in enumerate(cats, 1)],
        "category": cats, "subcategory": subs,
        "unit_cost": cost,
        "list_price": np.round(cost * rng.uniform(1.15, 1.6, n_prod), 2),
        "reorder_point": 0,                         # filled in after inventory simulation
        "supplier_key": rng.integers(1, n_sup + 1, n_prod),
    })

    customers = pd.DataFrame({
        "customer_key": range(1, n_cust + 1),
        "customer_name": [fake.name() for _ in range(n_cust)],
        "segment": rng.choice(["Retail", "Wholesale", "Corporate"], n_cust, p=[.6, .25, .15]),
        "region": rng.choice(["West", "North", "South", "East"], n_cust, p=[.35, .25, .25, .15]),
        "city": [fake.city() for _ in range(n_cust)],
    })

    # ---------- orders -> order lines ----------
    w = np.where(dates.month.isin([10, 11, 12]), 1.5, 1.0) * np.where(dates.dayofweek >= 5, 0.7, 1.0)
    w = w / w.sum()
    orders = pd.DataFrame({
        "order_id": [f"SO-{i:07d}" for i in range(1, n_orders + 1)],
        "order_date": rng.choice(dates.to_numpy(), n_orders, p=w),
        "customer_key": rng.choice(customers.customer_key.to_numpy(), n_orders),
        "n_lines": rng.integers(1, 6, n_orders),
    })
    lines = (orders.loc[orders.index.repeat(orders.n_lines)]
             .drop(columns="n_lines").reset_index(drop=True))

    pop = rng.pareto(1.2, n_prod) + 1               # Pareto-like SKU popularity
    pop = pop / pop.sum()
    lines["product_key"] = rng.choice(products.product_key.to_numpy(), len(lines), p=pop)
    lines = lines.drop_duplicates(["order_id", "product_key"]).reset_index(drop=True)
    lines = lines.merge(products[["product_key", "category", "unit_cost", "list_price"]], on="product_key")
    lines = lines.merge(customers[["customer_key", "segment"]], on="customer_key")

    # story: declining category
    t = (lines.order_date - start).dt.days / (len(dates) - 1)
    drop = (lines.category == DECLINING_CATEGORY) & (rng.random(len(lines)) < 0.6 * t)
    lines = lines[~drop].sort_values(["order_date", "order_id"]).reset_index(drop=True)
    t = (lines.order_date - start).dt.days / (len(dates) - 1)

    lines.insert(0, "order_line_id", np.arange(1, len(lines) + 1))
    base = rng.poisson(3, len(lines)) + 1
    mult = np.where(lines.segment == "Wholesale", 5, np.where(lines.segment == "Corporate", 3, 1))
    lines["qty_ordered"] = base * mult
    short = rng.random(len(lines)) < 0.08           # ~8% of lines are short-shipped
    frac = rng.uniform(0.5, 0.95, len(lines))
    lines["qty_shipped"] = np.where(short, np.floor(lines.qty_ordered * frac), lines.qty_ordered).astype(int)
    lines["discount_pct"] = rng.choice([0, 0.05, 0.10, 0.15], len(lines), p=[.6, .2, .15, .05])
    lines["unit_price"] = np.round(lines.list_price * rng.uniform(0.97, 1.03, len(lines)), 2)
    lines["unit_cost"] = np.round(lines.unit_cost * (1 + 0.04 * t), 2)   # mild cost inflation

    fact_sales = pd.DataFrame({
        "order_line_id": lines.order_line_id, "order_id": lines.order_id,
        "order_date_key": key(lines.order_date),
        "product_key": lines.product_key, "customer_key": lines.customer_key,
        "qty_ordered": lines.qty_ordered, "qty_shipped": lines.qty_shipped,
        "unit_price": lines.unit_price, "unit_cost": lines.unit_cost,
        "discount_pct": lines.discount_pct,
    })

    # ---------- weekly inventory simulation ----------
    snap_dates = pd.date_range(start, end, freq="7D")
    n_weeks = len(snap_dates)
    lines["week"] = ((lines.order_date - start).dt.days // 7).clip(upper=n_weeks - 1)
    demand = (lines.pivot_table(index="product_key", columns="week", values="qty_shipped",
                                aggfunc="sum", fill_value=0)
              .reindex(index=products.product_key, columns=range(n_weeks), fill_value=0))
    lead = suppliers.set_index("supplier_key").lead_time_days
    prone = set(rng.choice(products.product_key.to_numpy(),
                           int(n_prod * STOCKOUT_PRONE_SHARE), replace=False).tolist())

    inv_rows, reorder_points = [], {}
    for pk, sk in zip(products.product_key, products.supplier_key):
        d = demand.loc[pk].to_numpy()
        avg = max(d.mean(), 0.5)
        lead_w = int(np.ceil(lead[sk] / 7))
        rp = int(np.ceil(avg * (lead_w + 1)))
        order_qty = int(np.ceil(avg * (2 if pk in prone else 8)))   # prone SKUs under-order
        reorder_points[pk] = rp
        on_hand, pipeline = int(avg * 10), {}
        for wk in range(n_weeks):
            on_hand += pipeline.pop(wk, 0)
            on_hand = max(0, on_hand - int(d[wk]))
            on_order = sum(pipeline.values())
            if on_hand + on_order <= rp:
                pipeline[wk + lead_w] = pipeline.get(wk + lead_w, 0) + order_qty
                on_order += order_qty
            inv_rows.append((wk, pk, on_hand, on_order))
    products["reorder_point"] = products.product_key.map(reorder_points)

    inv = pd.DataFrame(inv_rows, columns=["week", "product_key", "on_hand_qty", "on_order_qty"])
    inv["snapshot_date_key"] = inv.week.map(lambda wk: int(snap_dates[wk].strftime("%Y%m%d")))
    inv.insert(0, "snapshot_id", np.arange(1, len(inv) + 1))
    inv = inv[["snapshot_id", "snapshot_date_key", "product_key", "on_hand_qty", "on_order_qty"]]

    # ---------- returns ----------
    sold = lines[lines.qty_shipped > 0]
    bad = set(rng.choice(products.product_key.to_numpy(), HIGH_RETURN_COUNT, replace=False).tolist())
    p_ret = np.where(sold.product_key.isin(bad), 0.25, 0.03)
    ret = sold[rng.random(len(sold)) < p_ret].copy()
    ret["qty_returned"] = [int(rng.integers(1, q + 1)) for q in ret.qty_shipped]
    ret["return_date"] = (ret.order_date
                          + pd.to_timedelta(rng.integers(3, 31, len(ret)), unit="D")).clip(upper=end)
    returns = pd.DataFrame({
        "return_id": np.arange(1, len(ret) + 1),
        "order_line_id": ret.order_line_id.to_numpy(),
        "return_date_key": key(ret.return_date).to_numpy(),
        "product_key": ret.product_key.to_numpy(),
        "qty_returned": ret.qty_returned.to_numpy(),
        "refund_amount": np.round(ret.qty_returned * ret.unit_price * (1 - ret.discount_pct), 2).to_numpy(),
        "reason": rng.choice(["Defective", "Wrong item", "Not as described", "Changed mind"],
                             len(ret), p=[.35, .2, .25, .2]),
    })

    # ---------- write ----------
    tables = {"dim_date": dim_date, "dim_supplier": suppliers, "dim_product": products,
              "dim_customer": customers, "fact_sales": fact_sales,
              "fact_inventory_snapshot": inv, "fact_returns": returns}
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)
        print(f"{name:28s}{len(df):>10,}")

    answer_key = {
        "declining_category": DECLINING_CATEGORY,
        "high_return_skus": sorted(products.loc[products.product_key.isin(bad), "sku"]),
        "stockout_prone_skus": sorted(products.loc[products.product_key.isin(prone), "sku"]),
    }
    (out / "_answer_key.json").write_text(json.dumps(answer_key, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", type=int, default=120_000)
    ap.add_argument("--out", default="data/raw")
    a = ap.parse_args()
    build(a.orders, a.out)