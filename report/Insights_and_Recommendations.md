# Online Retail II — Insights & Business Recommendations

**Dataset:** UK-based online retailer, Dec 2009 – Dec 2011
**Scope of analysis:** 1,021,403 cleaned transaction lines · 5,894 identified customers · 4,918 products · 43 countries

---

## 1. Headline Numbers

| Metric | Value |
|---|---|
| Total revenue (net of cancellations) | £19,666,308.83 |
| Total orders | 39,556 |
| Average order value | £497.18 |
| Average monthly revenue | £786,652.35 |
| Order-line cancellation rate | 1.76% |
| Revenue from guest checkouts (no Customer ID) | £2,593,456.54 (13.2% of revenue, 2,927 orders) |
| Revenue from identified customers | £17,072,852.29 (86.8% of revenue, 36,629 orders) |

---

## 2. Revenue Trend

- Revenue is highly seasonal: **every year, November is the peak month** (pre-Christmas ordering), with a sharp drop in January–February.
- 2010-11 (peak season) revenue is visibly higher than the equivalent months a year earlier, indicating the business grew year-over-year rather than staying flat.
- The month-over-month view (see `sql/01_revenue_and_country.sql`, Q1) shows growth is lumpy, not steady — this is typical of a B2B/wholesale-leaning retailer rather than pure steady-state D2C.

**Recommendation:** Plan inventory and staffing capacity around the September–November ramp-up specifically, rather than a flat month-over-month growth assumption. Consider a targeted email/discount campaign in the January–February trough to smooth revenue.

---

## 3. Country Performance

- **United Kingdom dominates**: 85.5% of revenue, 91.5% of orders. This is fundamentally a UK-first business with an international tail.
- Outside the UK, **EIRE (Ireland)** and the **Netherlands** are the top two international markets — but they behave very differently:
  - EIRE: very few unique customers (5) but very high average order value (~£1,052) → looks like a small number of large wholesale/reseller accounts.
  - Netherlands: 22 customers, average order value ~£2,545 → also wholesale-like behaviour, likely B2B resellers rather than individual consumers.

**Recommendation:** Treat the top 3–4 non-UK countries as key accounts to protect and grow (dedicated account management), rather than spreading international marketing spend thinly across 40+ countries where most contribute negligible revenue.

---

## 4. Product Performance

- **"REGENCY CAKESTAND 3 TIER"** is the single highest revenue product (~£330K), despite not being the highest-volume item — it has a high unit price and sells steadily.
- **"WHITE HANGING HEART T-LIGHT HOLDER"** and **"JUMBO BAG RED RETROSPOT"** are the next highest revenue products and also appear among the highest unit-volume sellers — genuine best-sellers, not just high-priced niche items.
- A distinct set of low-priced novelty items (e.g. "WORLD WAR 2 GLIDERS ASSTD DESIGNS") sell in very high volume but contribute comparatively little revenue — useful for basket-building/cross-sell, not as revenue drivers on their own.
- A small number of products show cancellation/return rates over 100% of units sold in a given period (more units cancelled than sold), which usually signals either a data-entry pattern (bulk pre-orders later cancelled) or a genuine product-quality/description-mismatch issue worth investigating manually.

**Recommendation:** Feature the top revenue products prominently in marketing and ensure they never go out of stock during the Sept–Nov ramp-up. Investigate the specific SKUs with cancellation rates above 50–100% — this is a short, actionable list, not a broad process fix.

---

## 5. Customer Segmentation (RFM)

Using Recency–Frequency–Monetary scoring (see `sql/03_rfm_and_segmentation.sql`):

| Segment | # Customers | % of Customers | Revenue | % of Revenue |
|---|---|---|---|---|
| Champions | 1,333 | 22.7% | £11.72M | 68.6% |
| At Risk | 1,339 | 22.9% | £3.26M | 19.1% |
| Needs Attention | 819 | 14.0% | £0.84M | 4.9% |
| *(remaining segments: Loyal, New/Promising, Lost/Churned)* | — | — | — | — |

**Key finding:** Roughly **23% of customers ("Champions") generate almost 69% of total revenue.** This is a classic Pareto pattern and the single most important insight for the business — customer retention in this top segment matters far more than acquiring new low-value customers.

**Recommendation:**
- Build a VIP / loyalty program specifically for the "Champions" segment — even a small increase in retention here has an outsized revenue impact.
- Run a win-back campaign (targeted discount or personal outreach) for the "At Risk" segment before they fully churn — they still represent ~19% of revenue and are not yet lost.
- Don't over-invest marketing budget on the long tail of "Needs Attention"/low-value customers relative to their revenue contribution.

---

## 6. Cohort Retention

Looking at monthly acquisition cohorts (see `sql/04_cohort_retention.sql`):

- Repeat purchase rate (customer places at least a 2nd order, ever) starts around **85–90%** for early cohorts (Dec 2009 – Jan 2010) and **declines for cohorts acquired later** in the dataset window.
- Month-1 retention (customers buying again in the very next month) typically sits in the **15–27% range (averaging ~21%)** across cohorts, with the very first cohort (Dec 2009) as a notable outlier at 35% — meaningful drop-off right after the first purchase, which is the normal pattern for retail but also the biggest lever: even a modest improvement in month-1 retention compounds significantly given how concentrated revenue is in repeat/loyal customers (see Section 5).

**Recommendation:** Introduce a "second purchase" nudge (reminder email/discount) targeted specifically at customers between 20–40 days after their first order, when they are most likely to drop off.

---

## 7. Data Quality Notes (for transparency)

- 34,335 exact duplicate rows were removed (~3.2% of raw rows) — likely re-exports/re-entries in the source system.
- ~13.2% of revenue comes from transactions with no Customer ID (guest/unregistered checkouts) — these are included in revenue and country analysis but **excluded from RFM, segmentation, and cohort analysis**, since those require a way to identify the same customer over time.
- Non-product administrative codes (postage, bank charges, samples, etc.) were removed before product-level analysis, so "top products" reflects genuine merchandise only.

Full removal log: `data/removed_rows_summary.csv`

---

## 8. Summary of Recommendations

1. Plan inventory/staffing around the Sep–Nov seasonal ramp, not flat monthly growth.
2. Treat top non-UK countries (EIRE, Netherlands, Germany) as key wholesale-style accounts.
3. Guarantee stock availability for the top 3–5 revenue products year-round.
4. Investigate the specific SKUs with abnormally high cancellation rates.
5. Launch a loyalty program for the "Champions" segment (23% of customers, 69% of revenue).
6. Run a win-back campaign for the "At Risk" segment before they churn fully.
7. Add an automated "second purchase" nudge 20–40 days after a customer's first order.
