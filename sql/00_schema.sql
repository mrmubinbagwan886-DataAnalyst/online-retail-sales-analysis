-- ============================================================
-- 00_schema.sql
-- Online Retail II - Database Schema
-- ============================================================
-- Star-schema style design: one fact table (fact_sales) +
-- two dimension tables (dim_customers, dim_products).
-- Built for SQLite; to port to PostgreSQL, change
-- INTEGER PRIMARY KEY AUTOINCREMENT -> SERIAL PRIMARY KEY.
-- ============================================================

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_customers;

CREATE TABLE dim_customers (
    customer_id     INTEGER PRIMARY KEY,   -- unique customer identifier
    country         TEXT                   -- customer's most common country
);

CREATE TABLE dim_products (
    stock_code      TEXT PRIMARY KEY,      -- unique product/SKU code
    description     TEXT                   -- most common product description for that code
);

CREATE TABLE fact_sales (
    sale_id             INTEGER PRIMARY KEY AUTOINCREMENT, -- surrogate key, one row per invoice line
    invoice_no          TEXT NOT NULL,       -- invoice number ("C" prefix = cancellation)
    stock_code          TEXT NOT NULL,       -- FK -> dim_products
    customer_id         INTEGER,             -- FK -> dim_customers (NULL = guest checkout)
    invoice_date        TEXT NOT NULL,       -- transaction timestamp
    quantity            INTEGER NOT NULL,    -- units sold (negative for cancellations)
    unit_price          REAL NOT NULL,       -- price per unit (GBP)
    line_revenue        REAL NOT NULL,       -- quantity * unit_price
    country             TEXT,                -- country recorded on this specific invoice line
    is_cancelled        INTEGER NOT NULL,    -- 1 = cancelled order, 0 = normal sale
    has_customer_id     INTEGER NOT NULL,    -- 1 = known customer, 0 = guest checkout
    invoice_year_month  TEXT NOT NULL,       -- "YYYY-MM", used for monthly trend queries
    FOREIGN KEY (stock_code) REFERENCES dim_products(stock_code),
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id)
);

CREATE INDEX idx_fact_sales_customer   ON fact_sales(customer_id);
CREATE INDEX idx_fact_sales_stock      ON fact_sales(stock_code);
CREATE INDEX idx_fact_sales_date       ON fact_sales(invoice_date);
CREATE INDEX idx_fact_sales_yearmonth  ON fact_sales(invoice_year_month);
