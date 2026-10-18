import pandas as pd

UPLOAD_REQUIRED = ["order_id", "order_date", "sku", "customer_id", "qty_ordered", "qty_shipped", "unit_price", "unit_cost"]


def map_upload(up: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Convert a user CSV into the fact_sales shape. Unknown SKUs/dates become NaN,
    which the validation checks then report as errors."""
    missing = [c for c in UPLOAD_REQUIRED if c not in up.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    dt = pd.to_datetime(up["order_date"], errors="coerce")
    return pd.DataFrame({
        "order_line_id": range(1, len(up) + 1),
        "order_id": up["order_id"].astype(str),
        "order_date_key": pd.to_numeric(dt.dt.strftime("%Y%m%d"), errors="coerce"),
        "product_key": up["sku"].map(products.set_index("sku").product_key),
        "customer_key": pd.to_numeric(up["customer_id"], errors="coerce"),
        "qty_ordered": up["qty_ordered"], "qty_shipped": up["qty_shipped"],
        "unit_price": up["unit_price"], "unit_cost": up["unit_cost"],
        "discount_pct": up["discount_pct"].fillna(0) if "discount_pct" in up else 0.0,
    })