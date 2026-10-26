import numpy as np
import pandas as pd


def safe_div(a, b):
    return a / b if b else float("nan")


def headline_kpis(df: pd.DataFrame) -> dict:
    gross = df.gross_revenue.sum()
    net = gross - df.discount_amount.sum() - df.refund_amount.sum()
    shipped = df.qty_shipped.sum()
    return {
        "gross_revenue": gross,
        "net_revenue": net,
        "gross_margin_pct": safe_div(net - df.cogs.sum(), net),
        "units_sold": int(shipped),
        "aov": safe_div(net, df.order_id.nunique()),
        "fill_rate": safe_div(shipped, df.qty_ordered.sum()),
        "return_rate": safe_div(df.qty_returned.sum(), shipped),
    }


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    d = df.assign(month=df.full_date.dt.to_period("M").dt.to_timestamp())
    g = d.groupby("month").agg(
        gross_revenue=("gross_revenue", "sum"), discounts=("discount_amount", "sum"),
        refunds=("refund_amount", "sum"), cogs=("cogs", "sum"), orders=("order_id", "nunique"))
    g["net_revenue"] = g.gross_revenue - g.discounts - g.refunds
    g["gross_margin_pct"] = (g.net_revenue - g.cogs) / g.net_revenue
    g["mom_growth"] = g.net_revenue.pct_change()     # first/last month may be partial; flag in UI
    return g.reset_index()


def by_dimension(df: pd.DataFrame, dim: str) -> pd.DataFrame:
    g = df.groupby(dim).agg(
        gross=("gross_revenue", "sum"), disc=("discount_amount", "sum"), ref=("refund_amount", "sum"),
        cogs=("cogs", "sum"), units=("qty_shipped", "sum"), returned=("qty_returned", "sum"))
    g["net_revenue"] = g.gross - g.disc - g.ref
    g["gross_margin_pct"] = (g.net_revenue - g.cogs) / g.net_revenue
    g["return_rate"] = (g.returned / g.units).replace([np.inf, -np.inf], np.nan)
    return g.sort_values("net_revenue", ascending=False).reset_index()


def abc_classification(df: pd.DataFrame, a: float = 0.80, b: float = 0.95) -> pd.DataFrame:
    s = (df.assign(net=df.gross_revenue - df.discount_amount - df.refund_amount)
           .groupby(["sku", "product_name", "category"], as_index=False).net.sum()
           .sort_values("net", ascending=False).reset_index(drop=True))
    s["cum_share"] = s.net.cumsum() / s.net.sum()
    prev = s.cum_share.shift(fill_value=0)           # share accumulated BEFORE this SKU
    s["abc_class"] = np.where(prev < a, "A", np.where(prev < b, "B", "C"))
    return s


# ---- inventory -------------------------------------------------------------
def latest_snapshot(inv: pd.DataFrame) -> pd.DataFrame:
    return inv[inv.snapshot_date == inv.snapshot_date.max()].copy()


def inventory_health(latest_inv, sales, window_days=30, overstock_days=120) -> pd.DataFrame:
    asof = sales.full_date.max()
    recent = sales[sales.full_date > asof - pd.Timedelta(days=window_days)]
    daily = (recent.groupby("sku").qty_shipped.sum() / window_days).rename("daily_units").reset_index()
    out = latest_inv.merge(daily, on="sku", how="left").fillna({"daily_units": 0})
    out["days_of_cover"] = np.where(out.daily_units > 0, out.on_hand_qty / out.daily_units, np.inf)
    out["stockout_risk"] = out.days_of_cover < out.lead_time_days
    out["overstock"] = out.days_of_cover > overstock_days
    return out


def stockout_rate(inv: pd.DataFrame) -> float:
    return float((inv.on_hand_qty == 0).mean()) if len(inv) else float("nan")


def inventory_turnover(cogs: float, inv: pd.DataFrame) -> float:
    value_per_snapshot = (inv.on_hand_qty * inv.unit_cost).groupby(inv.snapshot_date).sum()
    return safe_div(cogs, value_per_snapshot.mean())


def days_of_inventory(turnover: float, days_in_period: int) -> float:
    return safe_div(days_in_period, turnover)