import pandas as pd
import pytest

from etl.validate import has_errors, run_all


@pytest.fixture
def data():
    sales = pd.DataFrame(
        {
            "order_line_id": [1, 2],
            "order_id": ["O1", "O2"],
            "order_date_key": [20250110, 20250111],
            "product_key": [1, 2],
            "customer_key": [1, 1],
            "qty_ordered": [10, 5],
            "qty_shipped": [10, 5],
            "unit_price": [100.0, 200.0],
            "unit_cost": [60.0, 100.0],
            "discount_pct": [0.0, 0.1],
        }
    )
    return {
        "sales": sales,
        "products": pd.DataFrame({"product_key": [1, 2], "sku": ["A", "B"]}),
        "customers": pd.DataFrame({"customer_key": [1]}),
    }


def result(data, name):
    return {r.name: r for r in run_all(data)}[name]


def test_clean_data_has_no_errors(data):
    assert not has_errors(run_all(data))


def test_shipped_more_than_ordered_is_caught(data):
    data["sales"].loc[0, "qty_shipped"] = 99
    assert not result(data, "Shipped quantity <= ordered quantity").passed


def test_unknown_sku_is_caught(data):
    data["sales"].loc[0, "product_key"] = 999
    assert not result(data, "Every SKU exists in product master").passed


def test_future_date_is_caught(data):
    data["sales"].loc[0, "order_date_key"] = 20990101
    assert not result(data, "Dates valid and not in the future").passed


def test_bad_discount_is_caught(data):
    data["sales"].loc[0, "discount_pct"] = 1.5
    assert not result(data, "Discount between 0 and 1").passed


def test_missing_column_short_circuits(data):
    data["sales"] = data["sales"].drop(columns=["unit_cost"])
    res = run_all(data)
    assert len(res) == 1 and not res[0].passed


# ---------- remaining Error checks ----------


def test_duplicate_lines_are_caught(data):
    dup = data["sales"].iloc[[0]].copy()
    dup["order_line_id"] = 3  # same order + product, new line id
    data["sales"] = pd.concat([data["sales"], dup], ignore_index=True)
    assert not result(data, "No duplicate order lines").passed


def test_repeated_line_id_is_caught(data):
    data["sales"].loc[1, "order_line_id"] = 1
    assert not result(data, "order_line_id is unique").passed


def test_null_in_key_column_is_caught(data):
    data["sales"] = data["sales"].astype({"qty_ordered": float})
    data["sales"].loc[0, "qty_ordered"] = float("nan")
    assert not result(data, "No nulls in key/measure columns").passed


def test_negative_price_is_caught(data):
    data["sales"].loc[0, "unit_price"] = -5.0
    assert not result(data, "Prices and costs are non-negative").passed


def test_unknown_customer_is_caught(data):
    data["sales"].loc[0, "customer_key"] = 999
    assert not result(data, "Every customer exists in customer master").passed


def test_return_exceeding_shipped_is_caught(data):
    data["returns"] = pd.DataFrame(
        {"order_line_id": [1], "qty_returned": [99]}
    )  # shipped was 10
    assert not result(data, "Returned qty <= shipped qty").passed


def test_orphan_return_is_caught(data):
    data["returns"] = pd.DataFrame(
        {"order_line_id": [777], "qty_returned": [1]}
    )  # no such order line
    assert not result(data, "Returned qty <= shipped qty").passed


def test_valid_return_passes(data):
    data["returns"] = pd.DataFrame({"order_line_id": [1], "qty_returned": [3]})
    assert result(data, "Returned qty <= shipped qty").passed


def test_returns_check_skipped_without_returns_data(data):
    r = result(data, "Returned qty <= shipped qty")
    assert r.passed and "skipped" in r.detail


# ---------- Warning checks ----------


def test_price_below_cost_warns(data):
    data["sales"].loc[0, "unit_price"] = 10.0  # cost is 60
    r = result(data, "Unit price >= unit cost")
    assert not r.passed and r.severity == "Warning"


def test_warnings_do_not_block(data):
    data["sales"].loc[0, "unit_price"] = 10.0  # triggers a Warning only
    assert not has_errors(run_all(data))


def test_price_outlier_warns(data):
    n = 10
    data["sales"] = pd.DataFrame(
        {
            "order_line_id": range(1, n + 1),
            "order_id": [f"O{i}" for i in range(1, n + 1)],
            "order_date_key": [20250110] * n,
            "product_key": [1] * n,
            "customer_key": [1] * n,
            "qty_ordered": [5] * n,
            "qty_shipped": [5] * n,
            "unit_price": [100.0] * (n - 1) + [10000.0],  # one absurd price
            "unit_cost": [60.0] * n,
            "discount_pct": [0.0] * n,
        }
    )
    assert not result(data, "No extreme price outliers").passed


def test_inventory_gap_warns(data):
    data["inventory"] = pd.DataFrame(
        {
            "snapshot_date_key": [20250101, 20250301],  # ~2-month gap
            "product_key": [1, 1],
            "on_hand_qty": [10, 8],
        }
    )
    assert not result(data, "Inventory snapshots have no large gaps").passed


def test_weekly_inventory_snapshots_pass(data):
    data["inventory"] = pd.DataFrame(
        {
            "snapshot_date_key": [20250101, 20250108, 20250115],
            "product_key": [1, 1, 1],
            "on_hand_qty": [10, 9, 8],
        }
    )
    assert result(data, "Inventory snapshots have no large gaps").passed


def test_stale_data_warns(data):
    # the fixture's dates are in January 2025, so they are stale by definition
    assert not result(data, "Data is fresh").passed


def test_fresh_data_passes(data):
    yesterday = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
    data["sales"]["order_date_key"] = int(yesterday.strftime("%Y%m%d"))
    assert result(data, "Data is fresh").passed


# ---------- runner behaviour ----------


def test_crashing_check_is_reported_as_failure(data):
    data["sales"]["order_date_key"] = [
        "abc",
        "def",
    ]  # unparseable, makes the date check raise
    r = result(data, "Dates valid and not in the future")
    assert not r.passed and "crashed" in r.detail
