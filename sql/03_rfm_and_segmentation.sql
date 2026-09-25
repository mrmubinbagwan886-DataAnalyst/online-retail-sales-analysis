-- ============================================================
-- 03_rfm_and_segmentation.sql
-- Business questions: RFM analysis, Customer segmentation
-- ============================================================
-- RFM = Recency (days since last purchase), Frequency (number of
-- distinct orders), Monetary (total amount spent).
-- Only rows with a known customer_id and is_cancelled = 0 are used,
-- because you can't attribute an anonymous sale to a customer.

-- ------------------------------------------------------------
-- Q1. RFM base metrics per customer
-- "Reference date" = the day after the last invoice date in the
-- whole dataset - this simulates "today" for a recency calculation.
-- ------------------------------------------------------------
WITH reference_date AS (
    SELECT DATE(MAX(invoice_date), '+1 day') AS ref_date
    FROM fact_sales
),
customer_rfm AS (
    SELECT
        fs.customer_id,
        CAST(JULIANDAY((SELECT ref_date FROM reference_date)) - JULIANDAY(MAX(fs.invoice_date)) AS INTEGER) AS recency_days,
        COUNT(DISTINCT fs.invoice_no) AS frequency,
        ROUND(SUM(fs.line_revenue), 2) AS monetary
    FROM fact_sales fs
    WHERE fs.is_cancelled = 0
      AND fs.has_customer_id = 1
    GROUP BY fs.customer_id
)
SELECT * FROM customer_rfm
ORDER BY monetary DESC;


-- ------------------------------------------------------------
-- Q2. RFM scoring (1-5 scale) + customer segmentation
-- Uses NTILE() window function to split customers into quintiles
-- for each metric, then combines the three scores into a segment
-- label with a CASE expression. This is the standard RFM approach
-- used in real CRM / marketing analytics tools.
-- ------------------------------------------------------------
WITH reference_date AS (
    SELECT DATE(MAX(invoice_date), '+1 day') AS ref_date
    FROM fact_sales
),
customer_rfm AS (
    SELECT
        fs.customer_id,
        CAST(JULIANDAY((SELECT ref_date FROM reference_date)) - JULIANDAY(MAX(fs.invoice_date)) AS INTEGER) AS recency_days,
        COUNT(DISTINCT fs.invoice_no) AS frequency,
        ROUND(SUM(fs.line_revenue), 2) AS monetary
    FROM fact_sales fs
    WHERE fs.is_cancelled = 0
      AND fs.has_customer_id = 1
    GROUP BY fs.customer_id
),
rfm_scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        -- Lower recency_days is better -> reverse the quintile (6 - ntile)
        (6 - NTILE(5) OVER (ORDER BY recency_days)) AS r_score,
        NTILE(5) OVER (ORDER BY frequency)          AS f_score,
        NTILE(5) OVER (ORDER BY monetary)           AS m_score
    FROM customer_rfm
)
SELECT
    customer_id,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    (r_score + f_score + m_score) AS rfm_total_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 4 AND f_score >= 3                  THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2                  THEN 'New / Promising'
        WHEN r_score BETWEEN 2 AND 3 AND f_score >= 3        THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2  THEN 'Lost / Churned'
        ELSE 'Needs Attention'
    END AS customer_segment
FROM rfm_scored
ORDER BY rfm_total_score DESC;


-- ------------------------------------------------------------
-- Q3. Segment summary - how many customers and how much revenue
-- sits in each segment (this is the table you'd feed straight
-- into a Power BI card/bar chart)
-- ------------------------------------------------------------
WITH reference_date AS (
    SELECT DATE(MAX(invoice_date), '+1 day') AS ref_date
    FROM fact_sales
),
customer_rfm AS (
    SELECT
        fs.customer_id,
        CAST(JULIANDAY((SELECT ref_date FROM reference_date)) - JULIANDAY(MAX(fs.invoice_date)) AS INTEGER) AS recency_days,
        COUNT(DISTINCT fs.invoice_no) AS frequency,
        ROUND(SUM(fs.line_revenue), 2) AS monetary
    FROM fact_sales fs
    WHERE fs.is_cancelled = 0
      AND fs.has_customer_id = 1
    GROUP BY fs.customer_id
),
rfm_scored AS (
    SELECT
        customer_id,
        monetary,
        (6 - NTILE(5) OVER (ORDER BY recency_days)) AS r_score,
        NTILE(5) OVER (ORDER BY frequency)          AS f_score,
        NTILE(5) OVER (ORDER BY monetary)           AS m_score
    FROM customer_rfm
),
segmented AS (
    SELECT
        customer_id,
        monetary,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 4 AND f_score >= 3                  THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2                  THEN 'New / Promising'
            WHEN r_score BETWEEN 2 AND 3 AND f_score >= 3        THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2  THEN 'Lost / Churned'
            ELSE 'Needs Attention'
        END AS customer_segment
    FROM rfm_scored
)
SELECT
    customer_segment,
    COUNT(*) AS num_customers,
    ROUND(SUM(monetary), 2) AS segment_revenue,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_customers,
    ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 2) AS pct_of_revenue
FROM segmented
GROUP BY customer_segment
ORDER BY segment_revenue DESC;
