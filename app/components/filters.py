import pandas as pd
import streamlit as st

from app import config


def _to_date(value, default):
    """Parse a query-param string into a date. Falls back to `default` if missing or invalid."""
    if not value:
        return default
    ts = pd.to_datetime(value, errors="coerce")
    return default if pd.isna(ts) else ts.date()


def role_selector() -> str:
    qp = st.query_params
    default = qp.get("role", "Executive")
    idx = config.ROLES.index(default) if default in config.ROLES else 0
    role = st.sidebar.selectbox("View as", config.ROLES, index=idx)
    st.query_params["role"] = role
    return role


def sidebar_filters(df: pd.DataFrame):
    """Returns (filtered, prior_period, meta). State is mirrored into the URL."""
    qp = st.query_params
    lo, hi = df.full_date.min().date(), df.full_date.max().date()

    start = _to_date(qp.get("from"), lo)
    end = _to_date(qp.get("to"), hi)
    start, end = min(max(start, lo), hi), min(max(end, lo), hi)   # clamp to the data's range
    if start > end:
        start, end = lo, hi

    st.sidebar.header("Filters")
    picked = st.sidebar.date_input("Date range", value=(start, end), min_value=lo, max_value=hi)
    if not isinstance(picked, (tuple, list)) or len(picked) != 2:
        st.info("Select an end date to continue.")
        st.stop()
    start, end = picked

    selections = {}
    for col, label in [("category", "Category"), ("region", "Region"), ("segment", "Segment")]:
        options = sorted(df[col].dropna().unique())
        default = [v for v in qp.get_all(col) if v in options]
        selections[col] = st.sidebar.multiselect(label, options, default=default)

    st.query_params["from"], st.query_params["to"] = start.isoformat(), end.isoformat()
    for col, vals in selections.items():
        if vals:
            st.query_params[col] = vals
        elif col in st.query_params:
            del st.query_params[col]

    base = df
    for col, vals in selections.items():
        if vals:
            base = base[base[col].isin(vals)]

    s, e = pd.Timestamp(start), pd.Timestamp(end)
    current = base[(base.full_date >= s) & (base.full_date <= e)]
    span = (e - s).days + 1
    prior = base[(base.full_date >= s - pd.Timedelta(days=span)) & (base.full_date < s)]
    meta = {"from": start, "to": end, **selections}
    return current, prior, meta