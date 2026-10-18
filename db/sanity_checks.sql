-- 1. Rows exist in every table
SELECT 'sales', COUNT(*) FROM fact_sales UNION ALL SELECT 'inventory', COUNT(*) FROM fact_inventory_snapshot;

-- 2. Seasonality is visible
SELECT year, month, ROUND(SUM(gross_revenue)) AS rev FROM vw_sales_enriched GROUP BY 1,2 ORDER BY 1,2;

-- 3. Pareto: top 20% of SKUs should hold well over half the revenue
SELECT sku, ROUND(SUM(gross_revenue)) AS rev FROM vw_sales_enriched GROUP BY sku ORDER BY rev DESC LIMIT 10;

-- 4. The Home Decor decline: compare first and last 3 months
SELECT year, month, ROUND(SUM(gross_revenue)) FROM vw_sales_enriched WHERE category='Home Decor' GROUP BY 1,2 ORDER BY 1,2;