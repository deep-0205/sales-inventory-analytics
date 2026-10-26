import pandas as pd
import streamlit as st

from etl import transform, validate

ss = st.session_state
st.title("Data & Quality")

latest = ss["sales_all"].full_date.max()
st.metric(
    "Latest order date in database",
    latest.strftime("%d %b %Y"),
    f"{(pd.Timestamp.today().normalize() - latest).days} days ago",
    delta_color="off",
)

st.subheader("Upload sales data (CSV)")
st.caption("Required columns: " + ", ".join(transform.UPLOAD_REQUIRED))
file = st.file_uploader("CSV file", type="csv")
if file:
    try:
        products = ss["sales_all"][["sku"]].drop_duplicates()
        # Needs product_key; load the dimension from the database or from sales_all as in your design
        # (see note below).
        mapped = transform.map_upload(pd.read_csv(file), ss["product_dim"])
        results = validate.run_all(
            {
                "sales": mapped,
                "products": ss["product_dim"],
                "customers": ss["customer_dim"],
            }
        )
        for r in results:
            icon = "✅" if r.passed else ("❌" if r.severity == "Error" else "⚠️")
            st.write(f"{icon} **{r.name}**: {r.detail}")
        if validate.has_errors(results):
            st.error("Fix the errors above and re-upload.")
        else:
            st.success("Validation passed.")
    except ValueError as e:
        st.error(str(e))
