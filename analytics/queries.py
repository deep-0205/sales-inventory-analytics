import pandas as pd

SALES_SQL = """
SELECT v.*, COALESCE(r.qty_returned, 0) AS qty_returned, COALESCE(r.refund_amount, 0) AS refund_amount
FROM vw_sales_enriched v
LEFT JOIN (SELECT order_line_id, SUM(qty_returned) AS qty_returned, SUM(refund_amount) AS refund_amount
FROM fact_returns GROUP BY order_line_id) r USING (order_line_id)
"""

INVENTORY_SQL = """
SELECT d.full_date AS snapshot_date, p.sku, p.product_name, p.category, p.unit_cost,
s.lead_time_days, i.on_hand_qty, i.on_order_qty
FROM fact_inventory_snapshot i
JOIN dim_date d ON d.date_key = i.snapshot_date_key
JOIN dim_product p ON p.product_key = i.product_key
JOIN dim_supplier s ON s.supplier_key = p.supplier_key
"""


def sales_enriched(con) -> pd.DataFrame:
    df = pd.read_sql_query(SALES_SQL, con)
    df["full_date"] = pd.to_datetime(df["full_date"])
    return df


def inventory_all(con) -> pd.DataFrame:
    df = pd.read_sql_query(INVENTORY_SQL, con)
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    return df
