# Power BI Dashboard — Build Guide (Online Retail II)

> **Note:** This guide was used to build `Online_Retail_II_Dashboard.pbix` (included in this repo). It's kept here as documentation of the data model, DAX measures, and design decisions behind the dashboard — useful for anyone reviewing the project or rebuilding the report from scratch.

A `.pbix` file can't be generated programmatically outside Power BI Desktop, so
this guide gives you the **exact steps** to build it yourself in ~30-45 minutes.
Everything you need (cleaned tables, DAX measures) is already prepared.

## Files you'll import

From the `data/` folder:
- `powerbi_fact_sales.csv` — the fact table (~1M rows, one per invoice line)
- `powerbi_dim_customers.csv` — one row per customer
- `powerbi_dim_products.csv` — one row per product

> These are already-cleaned exports of the same `fact_sales`, `dim_customers`,
> `dim_products` tables from `data/online_retail.db`. If you have the ODBC
> driver for SQLite installed, you can instead connect Power BI directly to
> the `.db` file (Get Data → ODBC) — the CSVs are the simpler, no-setup path.

---

## Step 1 — Import the data

1. Open Power BI Desktop → **Get Data → Text/CSV**.
2. Import all three CSVs listed above.
3. In **Power Query Editor**, check data types on load:
   - `fact_sales`: `invoice_date` → Date/Time, `quantity`/`unit_price`/`line_revenue` → Decimal Number, `is_cancelled`/`has_customer_id` → Whole Number (we'll treat 1/0 as flags).
   - `dim_customers`: `customer_id` → Whole Number.
   - `dim_products`: `stock_code` → Text.
4. Click **Close & Apply**.

## Step 2 — Build the data model (relationships)

Go to the **Model** view and create:

- `fact_sales[customer_id]` → `dim_customers[customer_id]` (Many-to-One, single direction)
- `fact_sales[stock_code]` → `dim_products[stock_code]` (Many-to-One, single direction)

Also create a **Date table** (best practice — do this rather than relying on `invoice_date` directly):

1. **Modeling → New Table**, paste:
   ```
   DateTable = CALENDAR(MIN(fact_sales[invoice_date]), MAX(fact_sales[invoice_date]))
   ```
2. Add helper columns on `DateTable`:
   ```
   Year = YEAR(DateTable[Date])
   MonthNumber = MONTH(DateTable[Date])
   MonthName = FORMAT(DateTable[Date], "MMM")
   YearMonth = FORMAT(DateTable[Date], "YYYY-MM")
   ```
3. Relate `DateTable[Date]` → `fact_sales[invoice_date]` (One-to-Many).
4. Mark `DateTable` as the official **Date Table** (right-click → Mark as Date Table).

## Step 3 — Core DAX measures

Create a new **Measures table** (Modeling → New Table → name it `_Measures`, just a blank placeholder table to keep measures organized) and add these:

```DAX
Total Revenue =
CALCULATE(
    SUM(fact_sales[line_revenue]),
    fact_sales[is_cancelled] = 0
)

Total Orders =
CALCULATE(
    DISTINCTCOUNT(fact_sales[invoice_no]),
    fact_sales[is_cancelled] = 0
)

Total Customers =
CALCULATE(
    DISTINCTCOUNT(fact_sales[customer_id]),
    fact_sales[has_customer_id] = 1,
    fact_sales[is_cancelled] = 0
)

Avg Order Value =
DIVIDE([Total Revenue], [Total Orders])

Cancellation Rate % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_sales), fact_sales[is_cancelled] = 1),
    COUNTROWS(fact_sales)
)

-- Time intelligence (needs the DateTable marked as date table)
Revenue MoM % =
VAR CurrentRevenue = [Total Revenue]
VAR PrevRevenue =
    CALCULATE([Total Revenue], DATEADD(DateTable[Date], -1, MONTH))
RETURN
    DIVIDE(CurrentRevenue - PrevRevenue, PrevRevenue)

Revenue YoY % =
VAR CurrentRevenue = [Total Revenue]
VAR PrevYearRevenue =
    CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(DateTable[Date]))
RETURN
    DIVIDE(CurrentRevenue - PrevYearRevenue, PrevYearRevenue)

Revenue Rank by Country =
RANKX(
    ALL(dim_customers[country]),
    [Total Revenue],
    ,
    DESC
)

Running Total Revenue =
CALCULATE(
    [Total Revenue],
    FILTER(
        ALLSELECTED(DateTable[Date]),
        DateTable[Date] <= MAX(DateTable[Date])
    )
)
```

### RFM / Customer Segment measures

Easiest approach: **import the RFM segment table directly** from
`sql/03_rfm_and_segmentation.sql` (Query 2) as its own table — run that
query, export the result to `data/powerbi_rfm_segments.csv`, and import it
like the other CSVs. Relate it to `dim_customers[customer_id]`.

Then a simple supporting measure:
```DAX
Customers per Segment =
DISTINCTCOUNT(rfm_segments[customer_id])

Revenue per Segment =
CALCULATE([Total Revenue], USERELATIONSHIP(rfm_segments[customer_id], fact_sales[customer_id]))
```

(If you'd rather not add a separate relationship, it's simpler to just use
the segment table's own `monetary` column directly for segment revenue —
it's already pre-aggregated per customer by the SQL query.)

## Step 4 — Build the report pages

**Page 1 — Executive Overview**
- 4 KPI cards across the top: `[Total Revenue]`, `[Total Orders]`, `[Avg Order Value]`, `[Total Customers]`
- Line chart: Revenue by `DateTable[YearMonth]` (X-axis) — this is your monthly trend
- Bar chart: Top 10 countries by `[Total Revenue]` (from `dim_customers[country]`)
- Map visual (Power BI's built-in **Map** or **Filled Map**): `dim_customers[country]` on Location, `[Total Revenue]` on size/color
- Slicers: Year, Country, Product Category (if you tag one) — placed at top or as a slicer panel on the left

**Page 2 — Product Performance**
- Table or bar chart: Top 20 products by `[Total Revenue]` (from `dim_products[description]`)
- Bar chart: Top 20 products by units sold
- Table: products with high cancellation rate (import the Q3 result from `sql/02_top_products.sql` as a supporting table if you want it interactive)

**Page 3 — Customer Segmentation (RFM)**
- Donut/pie chart: number of customers per segment
- Bar chart: revenue per segment
- Scatter chart: Recency (X) vs Frequency (Y), sized by Monetary, colored by segment — this is the classic RFM visual
- Table: top 20 "Champions" customers by monetary value

**Page 4 — Cohort / Retention**
- Matrix visual: `cohort_month` (rows) x `month_number` (columns), values = `retention_rate_pct` — this reproduces the classic cohort heatmap. Import the result of `sql/04_cohort_retention.sql` Query 2 as its own table for this.
- Apply **conditional formatting (color scale, green→red)** on the matrix values to make the retention drop-off visually obvious.
- Line chart: repeat purchase rate by cohort month (Query 3 result)

## Step 5 — Slicers & interactivity

- Add a slicer for `DateTable[Year]` and sync it across all pages (**View → Sync Slicers**).
- Add a slicer for `dim_customers[country]`.
- Add a slicer for `customer_segment` (from the RFM table) on the segmentation page.
- Turn on **cross-filtering** (default behavior) so clicking a country on the map filters the KPI cards and product table.

## Step 6 — Polish

- Set a consistent color theme (View → Themes).
- Format all revenue cards/axes as currency (`£#,##0`).
- Add tooltips: hovering a country on the map should show Revenue, Orders, Unique Customers (drag those fields into the Tooltips well of the Map visual).
- Add a title text box and your name/date as a footer for a portfolio-ready look.

## Step 7 — Save

Save as `Online_Retail_II_Dashboard.pbix`. If you want a "live" refreshable
version, keep the CSV files in a fixed folder path and use **Refresh** in
Power BI whenever the underlying SQLite database is rebuilt — you'd just
re-run the `03_build_kpi_excel.py`-style CSV export step first (or connect
directly via ODBC and refresh will read live from the `.db` file).
