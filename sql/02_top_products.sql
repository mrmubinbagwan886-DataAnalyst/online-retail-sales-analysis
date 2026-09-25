-- ============================================================
-- 02_top_products.sql
-- Business question: Top products by revenue and by quantity
-- ============================================================

-- ------------------------------------------------------------
-- Q1. Top 20 products by total revenue
-- ------------------------------------------------------------
SELECT
    fs.stock_code,
    dp.description,
    SUM(fs.quantity) AS total_units_sold,
    ROUND(SUM(fs.line_revenue), 2) AS total_revenue,
    COUNT(DISTINCT fs.invoice_no) AS times_ordered
FROM fact_sales fs
JOIN dim_products dp ON fs.stock_code = dp.stock_code
WHERE fs.is_cancelled = 0
GROUP BY fs.stock_code, dp.description
ORDER BY total_revenue DESC
LIMIT 20;


-- ------------------------------------------------------------
-- Q2. Top 20 products by units sold (volume leaders, may differ
-- from revenue leaders - useful for inventory planning)
-- ------------------------------------------------------------
SELECT
    fs.stock_code,
    dp.description,
    SUM(fs.quantity) AS total_units_sold,
    ROUND(SUM(fs.line_revenue), 2) AS total_revenue
FROM fact_sales fs
JOIN dim_products dp ON fs.stock_code = dp.stock_code
WHERE fs.is_cancelled = 0
GROUP BY fs.stock_code, dp.description
ORDER BY total_units_sold DESC
LIMIT 20;


-- ------------------------------------------------------------
-- Q3. Products with the highest cancellation/return rate
-- (rows where quantity was later reversed via a "C" invoice),
-- useful for spotting quality or listing-accuracy issues.
-- Uses a subquery to compute cancelled quantity per product.
-- ------------------------------------------------------------
SELECT
    dp.stock_code,
    dp.description,
    SUM(CASE WHEN fs.is_cancelled = 0 THEN fs.quantity ELSE 0 END) AS units_sold,
    ABS(SUM(CASE WHEN fs.is_cancelled = 1 THEN fs.quantity ELSE 0 END)) AS units_cancelled,
    ROUND(
        100.0 * ABS(SUM(CASE WHEN fs.is_cancelled = 1 THEN fs.quantity ELSE 0 END))
        / NULLIF(SUM(CASE WHEN fs.is_cancelled = 0 THEN fs.quantity ELSE 0 END), 0), 2
    ) AS cancellation_rate_pct
FROM fact_sales fs
JOIN dim_products dp ON fs.stock_code = dp.stock_code
GROUP BY dp.stock_code, dp.description
HAVING units_sold > 50   -- ignore low-volume noise
ORDER BY cancellation_rate_pct DESC
LIMIT 20;
