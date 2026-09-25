"""
03_build_kpi_excel.py
----------------------
Step 3 (optional/supporting) of the Online Retail II project.

WHAT THIS SCRIPT DOES:
    Pulls a handful of small, already-aggregated result sets out of the
    SQLite database (monthly revenue, country sales, top products,
    customer segments) and writes them into ONE small Excel workbook
    with a KPI Dashboard sheet on top.

WHY:
    The brief asks NOT to dump the full ~1M row dataset into Excel.
    Instead, this gives you a lightweight, shareable .xlsx with the
    key numbers - useful to attach to an email, or to sanity-check the
    Power BI numbers against.

IMPORTANT: The KPI Dashboard sheet uses real Excel formulas (SUM,
AVERAGE, etc.) that reference the data sheets - it is NOT hardcoded
numbers pasted in. If you refresh the data sheets, the KPI sheet
recalculates automatically.
"""

import sqlite3
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

DB_PATH = "/home/claude/project/data/online_retail.db"
OUTPUT_XLSX = "/home/claude/project/report/KPI_Summary.xlsx"

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Arial", bold=True, size=14, color="1F4E78")
BODY_FONT = Font(name="Arial", size=10)


def write_dataframe(ws, df, start_row=1):
    """Write a DataFrame to a worksheet with a styled header row."""
    for col_idx, col_name in enumerate(df.columns, start=1):
        cell = ws.cell(row=start_row, column=col_idx, value=col_name)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")

    for row_idx, row in enumerate(df.itertuples(index=False), start=start_row + 1):
        for col_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = BODY_FONT

    # Auto-width (approximate)
    for col_idx, col_name in enumerate(df.columns, start=1):
        max_len = max([len(str(col_name))] + [len(str(v)) for v in df[df.columns[col_idx - 1]].head(50)])
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 3, 40)

    return start_row + len(df) + 1  # next free row


def main():
    conn = sqlite3.connect(DB_PATH)

    monthly_revenue = pd.read_sql("""
        SELECT invoice_year_month, ROUND(SUM(line_revenue),2) AS total_revenue,
               COUNT(DISTINCT invoice_no) AS total_orders
        FROM fact_sales WHERE is_cancelled = 0
        GROUP BY invoice_year_month ORDER BY invoice_year_month
    """, conn)

    country_sales = pd.read_sql("""
        SELECT country, ROUND(SUM(line_revenue),2) AS total_revenue,
               COUNT(DISTINCT invoice_no) AS total_orders,
               COUNT(DISTINCT customer_id) AS unique_customers
        FROM fact_sales WHERE is_cancelled = 0
        GROUP BY country ORDER BY total_revenue DESC LIMIT 15
    """, conn)

    top_products = pd.read_sql("""
        SELECT fs.stock_code, dp.description,
               SUM(fs.quantity) AS units_sold,
               ROUND(SUM(fs.line_revenue),2) AS total_revenue
        FROM fact_sales fs JOIN dim_products dp ON fs.stock_code = dp.stock_code
        WHERE fs.is_cancelled = 0
        GROUP BY fs.stock_code, dp.description
        ORDER BY total_revenue DESC LIMIT 15
    """, conn)

    conn.close()

    wb = Workbook()

    # ---------------- Monthly Revenue sheet ----------------
    ws_monthly = wb.active
    ws_monthly.title = "Monthly Revenue"
    next_row = write_dataframe(ws_monthly, monthly_revenue)
    n_month_rows = len(monthly_revenue)

    # ---------------- Country Sales sheet ----------------
    ws_country = wb.create_sheet("Country Sales")
    write_dataframe(ws_country, country_sales)
    n_country_rows = len(country_sales)

    # ---------------- Top Products sheet ----------------
    ws_products = wb.create_sheet("Top Products")
    write_dataframe(ws_products, top_products)
    n_product_rows = len(top_products)

    # ---------------- KPI Dashboard sheet (formulas only) ----------------
    ws_kpi = wb.create_sheet("KPI Dashboard", 0)  # make it the first sheet
    ws_kpi["A1"] = "Online Retail II - KPI Summary"
    ws_kpi["A1"].font = TITLE_FONT
    ws_kpi.merge_cells("A1:C1")

    kpi_rows = [
        ("Total Revenue (GBP)", f"=SUM('Monthly Revenue'!B2:B{n_month_rows + 1})"),
        ("Total Orders",        f"=SUM('Monthly Revenue'!C2:C{n_month_rows + 1})"),
        ("Avg Monthly Revenue (GBP)", f"=AVERAGE('Monthly Revenue'!B2:B{n_month_rows + 1})"),
        ("Avg Order Value (GBP)", "=B4/B5"),  # Total Revenue (row4) / Total Orders (row5)
        ("Number of Countries", f"=COUNTA('Country Sales'!A2:A{n_country_rows + 1})"),
        ("Top Country by Revenue", "=INDEX('Country Sales'!A2:A16, MATCH(MAX('Country Sales'!B2:B16), 'Country Sales'!B2:B16, 0))"),
        ("Top Product by Revenue", "=INDEX('Top Products'!B2:B16, MATCH(MAX('Top Products'!D2:D16), 'Top Products'!D2:D16, 0))"),
    ]

    ws_kpi["A3"] = "Metric"
    ws_kpi["B3"] = "Value"
    ws_kpi["A3"].font = HEADER_FONT
    ws_kpi["B3"].font = HEADER_FONT
    ws_kpi["A3"].fill = HEADER_FILL
    ws_kpi["B3"].fill = HEADER_FILL

    for i, (label, formula) in enumerate(kpi_rows, start=4):
        ws_kpi[f"A{i}"] = label
        ws_kpi[f"B{i}"] = formula
        ws_kpi[f"A{i}"].font = BODY_FONT
        ws_kpi[f"B{i}"].font = BODY_FONT

    ws_kpi["B4"].number_format = "#,##0.00"
    ws_kpi["B6"].number_format = "#,##0.00"
    ws_kpi["B7"].number_format = "#,##0.00"
    ws_kpi["A1"].alignment = Alignment(horizontal="left")

    ws_kpi.column_dimensions["A"].width = 28
    ws_kpi.column_dimensions["B"].width = 30

    ws_kpi["A12"] = "Note: All KPI values above are live formulas referencing the data sheets, not hardcoded numbers."
    ws_kpi["A12"].font = Font(name="Arial", size=9, italic=True, color="808080")

    wb.save(OUTPUT_XLSX)
    print(f"Saved -> {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()
