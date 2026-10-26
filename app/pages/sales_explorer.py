import streamlit as st

from analytics import kpis
from app.components import charts

df = st.session_state["sales_f"]
st.title("Sales Explorer")

dim = st.selectbox(
    "Break down by", ["category", "subcategory", "region", "segment", "city"]
)
table = kpis.by_dimension(df, dim)
st.dataframe(
    table[[dim, "net_revenue", "gross_margin_pct", "units", "return_rate"]],
    hide_index=True,
    width="stretch",
    column_config={
        "net_revenue": st.column_config.NumberColumn(format="₹%.0f"),
        "gross_margin_pct": st.column_config.NumberColumn(format="percent"),
        "return_rate": st.column_config.NumberColumn(format="percent"),
    },
)
st.plotly_chart(
    charts.top_bottom_bar(table.head(15), "net_revenue", dim, f"Net revenue by {dim}"),
    width="stretch",
)
