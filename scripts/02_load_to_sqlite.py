"""
02_load_to_sqlite.py
---------------------
Step 2 of the Online Retail II end-to-end analytics project.

WHAT THIS SCRIPT DOES:
    Loads the cleaned CSV (from 01_clean_data.py) into a SQLite database
    using a proper, normalized schema instead of one flat table.

WHY SQLite (instead of PostgreSQL):
    SQLite needs zero setup (no server, no credentials, single .db file) -
    perfect for a portfolio project you want to share/run anywhere.
    Every query we write is standard SQL, so if you later want to move
    this to PostgreSQL for your portfolio, you can load the same CSVs
    with only minor syntax changes (e.g. AUTOINCREMENT -> SERIAL).

WHY A NORMALIZED SCHEMA (not one big flat table):
    A single flat table (like the raw Excel) repeats customer/product/
    country info on every single row - that's fine for Excel but it is
    NOT how a real analytics database should be designed. We split into:
        dim_customers   -> one row per customer
        dim_products    -> one row per product (stock_code)
        fact_sales      -> one row per invoice line (the actual transactions)
    This is a simple star schema: fact table + dimension tables.
    It mirrors how you'd design a real data warehouse, and it's exactly
    the kind of schema Power BI expects for good performance and clean
    relationships later.
"""

import pandas as pd
import sqlite3

CLEANED_CSV = "/home/claude/project/data/cleaned_retail_data.csv"
DB_PATH = "/home/claude/project/data/online_retail.db"

SCHEMA_SQL = """
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_customers;
DROP TABLE IF EXISTS dim_country;

CREATE TABLE dim_customers (
    customer_id     INTEGER PRIMARY KEY,
    country         TEXT
);

CREATE TABLE dim_products (
    stock_code      TEXT PRIMARY KEY,
    description     TEXT
);

CREATE TABLE fact_sales (
    sale_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no          TEXT NOT NULL,
    stock_code          TEXT NOT NULL,
    customer_id         INTEGER,
    invoice_date        TEXT NOT NULL,
    quantity            INTEGER NOT NULL,
    unit_price          REAL NOT NULL,
    line_revenue        REAL NOT NULL,
    country             TEXT,
    is_cancelled        INTEGER NOT NULL,
    has_customer_id     INTEGER NOT NULL,
    invoice_year_month  TEXT NOT NULL,
    FOREIGN KEY (stock_code) REFERENCES dim_products(stock_code),
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id)
);

CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_id);
CREATE INDEX idx_fact_sales_stock ON fact_sales(stock_code);
CREATE INDEX idx_fact_sales_date ON fact_sales(invoice_date);
CREATE INDEX idx_fact_sales_yearmonth ON fact_sales(invoice_year_month);
"""


def main():
    print("Reading cleaned CSV...")
    df = pd.read_csv(CLEANED_CSV, parse_dates=["invoice_date"])

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Creating schema (dim_customers, dim_products, fact_sales)...")
    cur.executescript(SCHEMA_SQL)
    conn.commit()

    # ------------------------------------------------------------------
    # dim_customers: one row per customer_id, only where customer_id
    # is known. We take the most frequent country for that customer
    # (a customer can occasionally show more than one country due to
    # data entry, so we pick the mode to keep the dimension table clean).
    # ------------------------------------------------------------------
    print("Building dim_customers...")
    customers_df = (
        df[df["has_customer_id"]]
        .groupby("customer_id")["country"]
        .agg(lambda x: x.mode().iloc[0])
        .reset_index()
    )
    customers_df.to_sql("dim_customers", conn, if_exists="append", index=False)

    # ------------------------------------------------------------------
    # dim_products: one row per stock_code, using the most common
    # description for that code (descriptions sometimes vary slightly
    # for the same stock_code across invoices).
    # ------------------------------------------------------------------
    print("Building dim_products...")
    products_df = (
        df.groupby("stock_code")["description"]
        .agg(lambda x: x.mode().iloc[0])
        .reset_index()
    )
    products_df.to_sql("dim_products", conn, if_exists="append", index=False)

    # ------------------------------------------------------------------
    # fact_sales: the actual transaction lines
    # ------------------------------------------------------------------
    print("Building fact_sales...")
    fact_df = df[[
        "invoice_no", "stock_code", "customer_id", "invoice_date",
        "quantity", "unit_price", "line_revenue", "country",
        "is_cancelled", "has_customer_id", "invoice_year_month",
    ]].copy()
    fact_df["invoice_date"] = fact_df["invoice_date"].astype(str)
    fact_df["is_cancelled"] = fact_df["is_cancelled"].astype(int)
    fact_df["has_customer_id"] = fact_df["has_customer_id"].astype(int)
    # customer_id can be NaN -> sqlite handles this as NULL automatically
    fact_df.to_sql("fact_sales", conn, if_exists="append", index=False)

    conn.commit()

    # ------------------------------------------------------------------
    # Quick sanity check
    # ------------------------------------------------------------------
    for table in ["dim_customers", "dim_products", "fact_sales"]:
        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count:,} rows")

    conn.close()
    print(f"\nSQLite database ready -> {DB_PATH}")


if __name__ == "__main__":
    main()
