import pandas as pd
import pytest
from etl.validate import run_all, has_errors


@pytest.fixture
def data():
    sales = pd.DataFrame({
        "order_line_id": [1, 2], "order_id": ["O1", "O2"],
        "order_date_key": [20250110, 20250111], "product_key": [1, 2], "customer_key": [1, 1],
        "qty_ordered": [10, 5], "qty_shipped": [10, 5],
        "unit_price": [100.0, 200.0], "unit_cost": [60.0, 100.0], "discount_pct": [0.0, 0.1]})
    return {"sales": sales,
            "products": pd.DataFrame({"product_key": [1, 2], "sku": ["A", "B"]}),
            "customers": pd.DataFrame({"customer_key": [1]})}


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