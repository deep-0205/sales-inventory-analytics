import streamlit as st

from analytics import kpis
from app import config
from app.components import charts
from app.components.kpi_cards import render_cards

ss = st.session_state
df, prior, role = ss["sales_f"], ss["sales_prior"], ss["role"]

st.title("Overview")
if df.empty:
    st.warning("No data for the selected filters. Try widening the date range.")
    st.stop()

cur = kpis.headline_kpis(df)
prev = kpis.headline_kpis(prior) if len(prior) else None
render_cards(cur, prev, config.ROLE_KPIS[role])

st.subheader("Net revenue and margin by month")
st.plotly_chart(charts.revenue_trend(kpis.monthly_trend(df)), width="stretch")
st.caption("First and last months may be partial.")

left, right = st.columns(2)
skus = kpis.by_dimension(df, "sku")
left.plotly_chart(charts.top_bottom_bar(skus.head(10), "net_revenue", "sku", "Top 10 SKUs"), width="stretch")
right.plotly_chart(charts.top_bottom_bar(skus.tail(10), "net_revenue", "sku", "Bottom 10 SKUs"), width="stretch")