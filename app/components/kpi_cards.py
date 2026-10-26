import pandas as pd
import streamlit as st

CARDS = {  # key: (label, kind, lower_is_better)
    "net_revenue": ("Net revenue", "inr", False), "gross_margin_pct": ("Gross margin", "pct", False),
    "aov": ("Avg order value", "inr", False), "units_sold": ("Units sold", "num", False),
    "fill_rate": ("Fill rate", "pct", False), "return_rate": ("Return rate", "pct", True),
}


def inr(x):
    if pd.isna(x):
        return "n/a"
    if abs(x) >= 1e7:
        return f"₹{x/1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x/1e5:.2f} L"
    return f"₹{x:,.0f}"


FMT = {"inr": inr, "pct": lambda x: "n/a" if pd.isna(x) else f"{x*100:.1f}%", "num": lambda x: f"{x:,.0f}"}


def render_cards(cur: dict, prev: dict | None, keys: list[str]):
    for col, k in zip(st.columns(len(keys)), keys):
        label, kind, lower_better = CARDS[k]
        delta = None
        if prev and not pd.isna(prev.get(k, float("nan"))) and prev[k] != 0:
            delta = f"{(cur[k]-prev[k])*100:+.1f} pp" if kind == "pct" else f"{(cur[k]/prev[k]-1)*100:+.1f}%"
        col.metric(label, FMT[kind](cur[k]), delta, delta_color="inverse" if lower_better else "normal")