import streamlit as st

from analytics import kpis
from app.components import charts

ss = st.session_state
sales_all, inv = ss["sales_all"], ss["inventory"]
st.title("Inventory Health")

health = kpis.inventory_health(kpis.latest_snapshot(inv), sales_all)
cats = ss["filters"]["category"]
if cats:
    health = health[health.category.isin(cats)]

c1, c2, c3 = st.columns(3)
c1.metric("SKUs at stockout risk", int(health.stockout_risk.sum()))
c2.metric("Overstocked SKUs", int(health.overstock.sum()))
c3.metric("Stockout rate (weekly snapshots)", f"{kpis.stockout_rate(inv) * 100:.1f}%")

view = st.radio("Show", ["Stockout risk", "Overstock", "All"], horizontal=True)
t = {
    "Stockout risk": health[health.stockout_risk],
    "Overstock": health[health.overstock],
    "All": health,
}[view]
st.dataframe(
    t.sort_values("days_of_cover")[
        [
            "sku",
            "product_name",
            "category",
            "on_hand_qty",
            "daily_units",
            "days_of_cover",
            "lead_time_days",
        ]
    ],
    hide_index=True,
    width="stretch",
)

st.subheader("ABC analysis")
abc = kpis.abc_classification(sales_all)
st.plotly_chart(charts.pareto(abc), width="stretch")
st.write(
    abc.groupby("abc_class").agg(skus=("sku", "count"), net_revenue=("net", "sum"))
)
