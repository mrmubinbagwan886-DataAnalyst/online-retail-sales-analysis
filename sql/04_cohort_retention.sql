-- ============================================================
-- 04_cohort_retention.sql
-- Business question: Cohort / retention analysis
-- ============================================================
-- A "cohort" here = the month a customer made their FIRST purchase.
-- We then track, for each cohort, how many of those customers came
-- back and bought again in each following month. This is the
-- classic cohort retention table used in subscription/e-commerce
-- analytics.

-- ------------------------------------------------------------
-- Q1. Assign each customer to a cohort month (their first order month)
-- and build the cohort x activity-month retention matrix.
-- ------------------------------------------------------------
WITH customer_orders AS (
    SELECT
        customer_id,
        invoice_no,
        invoice_year_month,
        MIN(invoice_year_month) OVER (PARTITION BY customer_id) AS cohort_month
    FROM fact_sales
    WHERE is_cancelled = 0
      AND has_customer_id = 1
    GROUP BY customer_id, invoice_no, invoice_year_month
),
cohort_activity AS (
    SELECT DISTINCT
        customer_id,
        cohort_month,
        invoice_year_month AS activity_month,
        -- month_number = how many months after the cohort's first
        -- purchase this activity happened (0 = the first month itself)
        -- NOTE: must reference invoice_year_month directly here, not the
        -- activity_month alias - SQLite (like standard SQL) does not let
        -- you reuse a column alias inside the same SELECT list.
        (
            (CAST(strftime('%Y', invoice_year_month || '-01') AS INTEGER) - CAST(strftime('%Y', cohort_month || '-01') AS INTEGER)) * 12
            + (CAST(strftime('%m', invoice_year_month || '-01') AS INTEGER) - CAST(strftime('%m', cohort_month || '-01') AS INTEGER))
        ) AS month_number
    FROM customer_orders
)
SELECT
    cohort_month,
    month_number,
    COUNT(DISTINCT customer_id) AS active_customers
FROM cohort_activity
GROUP BY cohort_month, month_number
ORDER BY cohort_month, month_number;


-- ------------------------------------------------------------
-- Q2. Retention rate (%) = active_customers in month N / cohort size
-- (cohort size = active_customers where month_number = 0)
-- This is the table you'd pivot in Power BI / Excel into the classic
-- "cohort triangle" heatmap.
-- ------------------------------------------------------------
WITH customer_orders AS (
    SELECT
        customer_id,
        invoice_no,
        invoice_year_month,
        MIN(invoice_year_month) OVER (PARTITION BY customer_id) AS cohort_month
    FROM fact_sales
    WHERE is_cancelled = 0
      AND has_customer_id = 1
    GROUP BY customer_id, invoice_no, invoice_year_month
),
cohort_activity AS (
    SELECT DISTINCT
        customer_id,
        cohort_month,
        invoice_year_month AS activity_month,
        (
            (CAST(strftime('%Y', invoice_year_month || '-01') AS INTEGER) - CAST(strftime('%Y', cohort_month || '-01') AS INTEGER)) * 12
            + (CAST(strftime('%m', invoice_year_month || '-01') AS INTEGER) - CAST(strftime('%m', cohort_month || '-01') AS INTEGER))
        ) AS month_number
    FROM customer_orders
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
    FROM cohort_activity
    WHERE month_number = 0
    GROUP BY cohort_month
),
cohort_counts AS (
    SELECT cohort_month, month_number, COUNT(DISTINCT customer_id) AS active_customers
    FROM cohort_activity
    GROUP BY cohort_month, month_number
)
SELECT
    cc.cohort_month,
    cc.month_number,
    cc.active_customers,
    cs.cohort_size,
    ROUND(100.0 * cc.active_customers / cs.cohort_size, 2) AS retention_rate_pct
FROM cohort_counts cc
JOIN cohort_sizes cs ON cc.cohort_month = cs.cohort_month
ORDER BY cc.cohort_month, cc.month_number;


-- ------------------------------------------------------------
-- Q3. Simple "repeat purchase rate" per cohort - what % of a
-- cohort ever placed a SECOND order (month_number >= 1), a
-- simpler retention headline number for an exec summary.
-- ------------------------------------------------------------
WITH customer_orders AS (
    SELECT
        customer_id,
        invoice_no,
        invoice_year_month,
        MIN(invoice_year_month) OVER (PARTITION BY customer_id) AS cohort_month
    FROM fact_sales
    WHERE is_cancelled = 0
      AND has_customer_id = 1
    GROUP BY customer_id, invoice_no, invoice_year_month
),
cohort_activity AS (
    SELECT DISTINCT
        customer_id,
        cohort_month,
        invoice_year_month AS activity_month
    FROM customer_orders
),
flagged AS (
    SELECT
        customer_id,
        cohort_month,
        MAX(CASE WHEN activity_month > cohort_month THEN 1 ELSE 0 END) AS repeated
    FROM cohort_activity
    GROUP BY customer_id, cohort_month
)
SELECT
    cohort_month,
    COUNT(*) AS cohort_size,
    SUM(repeated) AS customers_who_repeated,
    ROUND(100.0 * SUM(repeated) / COUNT(*), 2) AS repeat_purchase_rate_pct
FROM flagged
GROUP BY cohort_month
ORDER BY cohort_month;
