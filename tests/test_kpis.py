import pandas as pd
import pytest

from analytics.kpis import abc_classification, headline_kpis, inventory_health


@pytest.fixture
def sales():
    return pd.DataFrame(
        {
            "order_id": ["O1", "O2"],
            "sku": ["A", "B"],
            "product_name": ["A", "B"],
            "category": ["X", "X"],
            "full_date": pd.to_datetime(["2025-01-10", "2025-02-10"]),
            "qty_ordered": [10, 6],
            "qty_shipped": [10, 5],
            "gross_revenue": [1000.0, 1000.0],
            "discount_amount": [100.0, 0.0],
            "cogs": [600.0, 500.0],
            "qty_returned": [1, 0],
            "refund_amount": [50.0, 0.0],
        }
    )


def test_headline_kpis(sales):
    k = headline_kpis(sales)
    assert k["net_revenue"] == pytest.approx(1850)  # 2000 - 100 - 50
    assert k["gross_margin_pct"] == pytest.approx(750 / 1850)  # (1850 - 1100) / 1850
    assert k["aov"] == pytest.approx(925)
    assert k["fill_rate"] == pytest.approx(15 / 16)
    assert k["return_rate"] == pytest.approx(1 / 15)


def test_abc_boundaries(sales):
    # net: A=850, B=1000 -> B first (share 54%), then A (100%)
    r = abc_classification(sales, a=0.5, b=0.95).set_index("sku")
    assert r.loc["B", "abc_class"] == "A"
    assert r.loc["A", "abc_class"] == "B"


def test_empty_frame_does_not_crash(sales):
    k = headline_kpis(sales.iloc[0:0])
    assert k["net_revenue"] == 0 and pd.isna(k["aov"])


def test_inventory_risk_and_overstock():
    sales = pd.DataFrame(
        {"sku": ["B"], "qty_shipped": [30], "full_date": pd.to_datetime(["2025-03-01"])}
    )
    inv = pd.DataFrame(
        {"sku": ["A", "B"], "on_hand_qty": [500, 5], "lead_time_days": [20, 10]}
    )
    r = inventory_health(inv, sales).set_index("sku")
    assert r.loc["B", "stockout_risk"]  # 1 unit/day, 5 on hand => 5 days < 10 lead time
    assert r.loc["A", "overstock"]  # no recent demand => infinite cover
