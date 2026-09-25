"""
01_clean_data.py
-----------------
Step 1 of the Online Retail II end-to-end analytics project.

WHAT THIS SCRIPT DOES:
    1. Loads both sheets of the raw Excel file (Year 2009-2010, Year 2010-2011)
    2. Combines them into a single DataFrame
    3. Cleans the data (nulls, duplicates, data types, cancellations/returns)
    4. Saves a clean, analysis-ready CSV that we will load into SQLite in the
       next step (02_load_to_sqlite.py)

WHY WE DO IT IN PYTHON (and not Excel):
    The raw file has ~1.07 million rows. Excel becomes slow/unstable much
    before that and isn't built for reproducible, repeatable cleaning steps.
    pandas does this in a few seconds and the script itself becomes
    documentation of every decision we made.

This script intentionally sticks to basic pandas operations (filtering,
groupby, vectorized column math) - no custom classes, no advanced OOP,
nothing fancy. Just clean, readable, well-commented code.
"""

import pandas as pd
import numpy as np

RAW_FILE = "/mnt/user-data/uploads/online_retail_II.xlsx"
OUTPUT_CSV = "/home/claude/project/data/cleaned_retail_data.csv"
REMOVED_LOG_CSV = "/home/claude/project/data/removed_rows_summary.csv"


def load_raw_data(path: str) -> pd.DataFrame:
    """Load both yearly sheets and stack them into one DataFrame."""
    print("Loading Excel sheets... (this can take ~30-60 seconds for 1M+ rows)")
    sheet_2009_2010 = pd.read_excel(path, sheet_name="Year 2009-2010")
    sheet_2010_2011 = pd.read_excel(path, sheet_name="Year 2010-2011")

    df = pd.concat([sheet_2009_2010, sheet_2010_2011], ignore_index=True)
    print(f"Loaded {len(df):,} raw rows from both sheets.")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all cleaning steps and return a clean DataFrame.

    We keep a running log (removal_log) so the final report can state
    exactly how many rows were removed and why - this is important for
    any real analytics project: cleaning decisions must be transparent.
    """
    removal_log = []
    start_count = len(df)

    # ------------------------------------------------------------------
    # 1. Standardize column names (snake_case is easier to work with in
    #    pandas and later in SQL)
    # ------------------------------------------------------------------
    df = df.rename(columns={
        "Invoice": "invoice_no",
        "StockCode": "stock_code",
        "Description": "description",
        "Quantity": "quantity",
        "InvoiceDate": "invoice_date",
        "Price": "unit_price",
        "Customer ID": "customer_id",
        "Country": "country",
    })

    # ------------------------------------------------------------------
    # 2. Fix data types
    # ------------------------------------------------------------------
    df["invoice_no"] = df["invoice_no"].astype(str).str.strip()
    df["stock_code"] = df["stock_code"].astype(str).str.strip()
    df["description"] = df["description"].astype(str).str.strip()
    df["country"] = df["country"].astype(str).str.strip()
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
    # Customer ID has NaNs, so keep it as a nullable float first, we will
    # convert to nullable integer (Int64) after dropping/handling nulls.

    # ------------------------------------------------------------------
    # 3. Remove exact duplicate rows
    # ------------------------------------------------------------------
    before = len(df)
    df = df.drop_duplicates()
    removal_log.append(("exact_duplicate_rows", before - len(df)))

    # ------------------------------------------------------------------
    # 4. Handle missing Description (a few hundred rows have blank/garbage
    #    descriptions, mostly free-text adjustment entries - drop them)
    # ------------------------------------------------------------------
    before = len(df)
    df = df[df["description"].notna() & (df["description"].str.strip() != "") & (df["description"].str.lower() != "nan")]
    removal_log.append(("missing_or_blank_description", before - len(df)))

    # ------------------------------------------------------------------
    # 5. Flag cancelled invoices (Invoice numbers starting with "C").
    #    These are returns, not sales. We KEEP them in a separate flag
    #    (is_cancelled) instead of silently deleting them, because
    #    "how much did we lose to returns" is itself a useful business
    #    question. But for revenue/KPI calculations we will filter them out.
    # ------------------------------------------------------------------
    df["is_cancelled"] = df["invoice_no"].str.startswith("C")

    # ------------------------------------------------------------------
    # 6. Remove non-product stock codes (postage, bank charges, samples,
    #    manual adjustments, etc.) - these are not real product sales and
    #    would distort "top products" / "top revenue" analysis.
    # ------------------------------------------------------------------
    non_product_codes = ["POST", "D", "M", "DOT", "BANK CHARGES", "AMAZONFEE",
                          "PADS", "CRUK", "C2", "S", "TEST001", "TEST002"]
    before = len(df)
    df = df[~df["stock_code"].str.upper().isin(non_product_codes)]
    removal_log.append(("non_product_stock_codes", before - len(df)))

    # ------------------------------------------------------------------
    # 7. Remove rows with unit_price <= 0 for genuine sales rows (price 0
    #    usually means a free giveaway / data entry error, not a real sale).
    #    Cancelled rows can legitimately have quantity < 0, so we only
    #    filter price here, not quantity.
    # ------------------------------------------------------------------
    before = len(df)
    df = df[df["unit_price"] > 0]
    removal_log.append(("zero_or_negative_unit_price", before - len(df)))

    # ------------------------------------------------------------------
    # 8. Remove rows where quantity is 0 (no actual transaction happened)
    # ------------------------------------------------------------------
    before = len(df)
    df = df[df["quantity"] != 0]
    removal_log.append(("zero_quantity", before - len(df)))

    # ------------------------------------------------------------------
    # 9. Handle missing Customer ID.
    #    ~20% of rows have no Customer ID (likely guest checkouts).
    #    We do NOT drop these rows - they are still real sales and matter
    #    for total revenue / country-wise / product analysis.
    #    But we DO need a clean flag, because RFM / cohort / customer
    #    segmentation analysis in SQL will need to filter these out
    #    (you cannot segment a customer you cannot identify).
    # ------------------------------------------------------------------
    df["has_customer_id"] = df["customer_id"].notna()
    # Keep customer_id as nullable integer type (Int64 supports NaN, unlike int64)
    df["customer_id"] = df["customer_id"].astype("Int64")

    # ------------------------------------------------------------------
    # 10. Remove rows with missing/invalid invoice_date (can't analyze
    #     trends without a valid date)
    # ------------------------------------------------------------------
    before = len(df)
    df = df[df["invoice_date"].notna()]
    removal_log.append(("missing_invoice_date", before - len(df)))

    # ------------------------------------------------------------------
    # 11. Create derived columns useful for every downstream step
    # ------------------------------------------------------------------
    df["line_revenue"] = df["quantity"] * df["unit_price"]
    df["invoice_year"] = df["invoice_date"].dt.year
    df["invoice_month"] = df["invoice_date"].dt.month
    df["invoice_year_month"] = df["invoice_date"].dt.to_period("M").astype(str)

    # ------------------------------------------------------------------
    # 12. Reset index and save the removal log
    # ------------------------------------------------------------------
    df = df.reset_index(drop=True)

    log_df = pd.DataFrame(removal_log, columns=["reason", "rows_removed"])
    log_df.loc[len(log_df)] = ["TOTAL_STARTING_ROWS", start_count]
    log_df.loc[len(log_df)] = ["TOTAL_FINAL_ROWS", len(df)]
    log_df.to_csv(REMOVED_LOG_CSV, index=False)

    print("\nCleaning summary:")
    print(log_df.to_string(index=False))

    return df


def main():
    df = load_raw_data(RAW_FILE)
    df_clean = clean_data(df)

    df_clean.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved cleaned data -> {OUTPUT_CSV}")
    print(f"Final shape: {df_clean.shape}")
    print(f"\nColumn dtypes:\n{df_clean.dtypes}")


if __name__ == "__main__":
    main()
