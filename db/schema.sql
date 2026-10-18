PRAGMA foreign_keys = ON;

-- ---------- Dimensions ----------
CREATE TABLE dim_date (
    date_key        INTEGER PRIMARY KEY,
    full_date       DATE    NOT NULL UNIQUE,
    year            INTEGER NOT NULL,
    quarter         INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    month_name      TEXT    NOT NULL,
    week_of_year    INTEGER NOT NULL,
    day_of_week     INTEGER NOT NULL,
    is_weekend      INTEGER NOT NULL CHECK (is_weekend IN (0,1))
);

CREATE TABLE dim_supplier (
    supplier_key    INTEGER PRIMARY KEY,
    supplier_name   TEXT    NOT NULL,
    country         TEXT,
    lead_time_days  INTEGER NOT NULL CHECK (lead_time_days >= 0)
);

CREATE TABLE dim_product (
    product_key     INTEGER PRIMARY KEY,
    sku             TEXT    NOT NULL UNIQUE,
    product_name    TEXT    NOT NULL,
    category        TEXT    NOT NULL,
    subcategory     TEXT,
    unit_cost       REAL    NOT NULL CHECK (unit_cost >= 0),
    list_price      REAL    NOT NULL CHECK (list_price >= 0),
    reorder_point   INTEGER,
    supplier_key    INTEGER REFERENCES dim_supplier(supplier_key)
);

CREATE TABLE dim_customer (
    customer_key    INTEGER PRIMARY KEY,
    customer_name   TEXT    NOT NULL,
    segment         TEXT,
    region          TEXT,
    city            TEXT
);

-- ---------- Facts ----------
CREATE TABLE fact_sales (
    order_line_id   INTEGER PRIMARY KEY,
    order_id        TEXT    NOT NULL,
    order_date_key  INTEGER NOT NULL REFERENCES dim_date(date_key),
    product_key     INTEGER NOT NULL REFERENCES dim_product(product_key),
    customer_key    INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    qty_ordered     INTEGER NOT NULL CHECK (qty_ordered > 0),
    qty_shipped     INTEGER NOT NULL CHECK (qty_shipped >= 0),
    unit_price      REAL    NOT NULL CHECK (unit_price >= 0),
    unit_cost       REAL    NOT NULL CHECK (unit_cost >= 0),
    discount_pct    REAL    NOT NULL DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 1),
    CHECK (qty_shipped <= qty_ordered)
);

CREATE TABLE fact_inventory_snapshot (
    snapshot_id        INTEGER PRIMARY KEY,
    snapshot_date_key  INTEGER NOT NULL REFERENCES dim_date(date_key),
    product_key        INTEGER NOT NULL REFERENCES dim_product(product_key),
    on_hand_qty        INTEGER NOT NULL CHECK (on_hand_qty >= 0),
    on_order_qty       INTEGER NOT NULL DEFAULT 0,
    UNIQUE (snapshot_date_key, product_key)
);

CREATE TABLE fact_returns (
    return_id        INTEGER PRIMARY KEY,
    order_line_id    INTEGER NOT NULL REFERENCES fact_sales(order_line_id),
    return_date_key  INTEGER NOT NULL REFERENCES dim_date(date_key),
    product_key      INTEGER NOT NULL REFERENCES dim_product(product_key),
    qty_returned     INTEGER NOT NULL CHECK (qty_returned > 0),
    refund_amount    REAL    NOT NULL CHECK (refund_amount >= 0),
    reason           TEXT
);

-- ---------- Indexes ----------
CREATE INDEX idx_sales_date     ON fact_sales(order_date_key);
CREATE INDEX idx_sales_product  ON fact_sales(product_key);
CREATE INDEX idx_sales_customer ON fact_sales(customer_key);
CREATE INDEX idx_inv_date_prod  ON fact_inventory_snapshot(snapshot_date_key, product_key);
CREATE INDEX idx_returns_prod   ON fact_returns(product_key);

-- ---------- Reporting view ----------
CREATE VIEW vw_sales_enriched AS
SELECT  s.order_line_id, s.order_id, d.full_date, d.year, d.month, d.month_name,
        p.sku, p.product_name, p.category, p.subcategory,
        c.segment, c.region, c.city,
        s.qty_ordered, s.qty_shipped, s.unit_price, s.unit_cost, s.discount_pct,
        s.qty_shipped * s.unit_price                         AS gross_revenue,
        s.qty_shipped * s.unit_price * s.discount_pct        AS discount_amount,
        s.qty_shipped * s.unit_cost                          AS cogs
FROM fact_sales s
JOIN dim_date     d ON d.date_key     = s.order_date_key
JOIN dim_product  p ON p.product_key  = s.product_key
JOIN dim_customer c ON c.customer_key = s.customer_key;
