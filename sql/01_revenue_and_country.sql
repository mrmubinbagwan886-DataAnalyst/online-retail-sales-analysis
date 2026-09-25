-- ============================================================
-- 01_revenue_and_country.sql
-- Business questions: Monthly revenue trend, Country-wise sales
-- ============================================================
-- NOTE: We always filter is_cancelled = 0 for revenue questions,
-- because cancelled orders are returns, not real sales.

-- ------------------------------------------------------------
-- Q1. Monthly revenue trend (with month-over-month % growth)
-- Uses a window function (LAG) to compare each month to the
-- previous month - this is the "advanced SQL" the brief asked for.
-- ------------------------------------------------------------
WITH monthly_revenue AS (
    SELECT
        invoice_year_month,
        ROUND(SUM(line_revenue), 2) AS total_revenue,
        COUNT(DISTINCT invoice_no) AS total_orders
    FROM fact_sales
    WHERE is_cancelled = 0
    GROUP BY invoice_year_month
)
SELECT
    invoice_year_month,
    total_revenue,
    total_orders,
    ROUND(total_revenue - LAG(total_revenue) OVER (ORDER BY invoice_year_month), 2) AS revenue_change_vs_prev_month,
    ROUND(
        100.0 * (total_revenue - LAG(total_revenue) OVER (ORDER BY invoice_year_month))
        / NULLIF(LAG(total_revenue) OVER (ORDER BY invoice_year_month), 0), 2
    ) AS revenue_growth_pct
FROM monthly_revenue
ORDER BY invoice_year_month;


-- ------------------------------------------------------------
-- Q2. Country-wise sales (revenue, orders, customers, avg order value)
-- ------------------------------------------------------------
SELECT
    country,
    ROUND(SUM(line_revenue), 2) AS total_revenue,
    COUNT(DISTINCT invoice_no) AS total_orders,
    COUNT(DISTINCT customer_id) AS unique_customers,
    ROUND(SUM(line_revenue) / COUNT(DISTINCT invoice_no), 2) AS avg_order_value,
    ROUND(
        100.0 * SUM(line_revenue) / SUM(SUM(line_revenue)) OVER (), 2
    ) AS pct_of_total_revenue
FROM fact_sales
WHERE is_cancelled = 0
GROUP BY country
ORDER BY total_revenue DESC;


-- ------------------------------------------------------------
-- Q3. Top 15 countries EXCLUDING the UK (UK dominates the dataset,
-- so this view is useful for looking at international performance)
-- ------------------------------------------------------------
SELECT
    country,
    ROUND(SUM(line_revenue), 2) AS total_revenue,
    COUNT(DISTINCT invoice_no) AS total_orders
FROM fact_sales
WHERE is_cancelled = 0
  AND country != 'United Kingdom'
GROUP BY country
ORDER BY total_revenue DESC
LIMIT 15;
