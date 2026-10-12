# Presentation Outline — Blood Bank Management Analytics Using MongoDB

## Slide 1 — Title and project overview

- Blood Bank Management Analytics Using MongoDB
- BDA mini project: synthetic inventory, donation, and hospital-request records
- Python/Pandas analytics, MongoDB storage, Streamlit dashboard
- Academic prototype; not a clinical decision system

**Speaker notes:** Introduce the problem area and state clearly that the data is synthetic. This project demonstrates database-backed analysis and visual reporting, not patient care.

## Slide 2 — Problem statement and objectives

- Stock and demand vary across dates, locations, banks, hospitals, and blood groups.
- A total-only shortage can hide shortages within a particular group.
- Validate records, calculate consistent indicators, compare trends, and present filtered results.
- Support safe inventory/request CRUD without destructive database seeding.

**Speaker notes:** Explain that O+ inventory cannot be counted as A+ stock. The objective is to make comparisons visible, not to decide where blood should be clinically allocated.

## Slide 3 — Sustainable Development Goal mapping

- **SDG 3:** educational support for visibility of blood availability and hospital demand.
- **SDG 10:** compare synthetic service indicators across locations for further investigation.
- **SDG 17:** model information shared between blood banks and hospitals.
- These are project alignments, not measured health outcomes or real partnerships.

**Speaker notes:** Describe each connection carefully. The project does not prove that it improved health, inequality, or institutional collaboration.

## Slide 4 — Technology stack and architecture

- Python: application and processing logic.
- Pandas: tabular validation, filtering, grouping, and statistics.
- MongoDB + PyMongo: document storage, queries, CRUD, and aggregation access.
- Plotly Express + Streamlit: interactive figures and dashboard UI.
- Pipeline: generate → validate → CSV/MongoDB → filter and analyze → visualize/export.

**Speaker notes:** Distinguish MongoDB, the database server, from PyMongo, its Python driver. Clarify that this small project demonstrates analytics but not distributed big-data processing.

## Slide 5 — Dataset and preprocessing

- Synthetic, deterministic records: 3 banks, 4 hospitals, 24 inventory records.
- 500 donations and 500 hospital requests; eight blood groups.
- Dates cover generated activity from 2024-01-01 to 2025-06-30.
- Validate IDs, duplicates, references, blood groups, dates, units, and request consistency.
- Current generated set: zero missing cells, duplicate rows, or rejected rows.

**Speaker notes:** Explain that a fixed random seed makes the generated dataset repeatable. Invalid records are reported and rejected, not silently “fixed.”

## Slide 6 — MongoDB collections and implementation

- `blood_banks`, `hospitals`, `blood_inventory`, `donations`, `hospital_requests`.
- Unique `_id` and named-ID indexes; secondary query indexes.
- Schema validators for inventory and requests; application-level reference checks.
- Additive seeding with `$setOnInsert`; does not reset or overwrite existing matched records.
- Local MongoDB verified; Atlas not verified.

**Speaker notes:** Show the actual collection names in the local database if available. Mention that MongoDB does not enforce relational foreign keys. Do not display connection strings or secrets.

## Slide 7 — Analytics methodology

- Fulfillment = total supplied ÷ total requested × 100.
- Pending = requested − supplied; preprocessing enforces consistency.
- Estimated shortage per group = max(pending − available stock, 0).
- Donation units grouped by day, Monday-starting week, and month.
- Mean, median, minimum, maximum, and sample standard deviation summarize selected records.

**Speaker notes:** State that shortage is a simplified group-level estimate, not a clinical recommendation. Filters apply to relevant records before calculations.

## Slide 8 — Dashboard and visualizations

- Sidebar filters: dates, blood group, hospital, location, blood bank.
- Inventory totals/distribution and configurable low-stock threshold.
- Hospital demand, supplied/pending units, weighted fulfillment.
- Daily/weekly/monthly donations; breakdowns by group, bank, location.
- Shortage rankings, descriptive statistics, and ZIP export of CSV tables.

**Speaker notes:** Demonstrate one filter change, then show an inventory chart, hospital comparison, and donation trend. Explain that inventory date uses `last_updated`.

## Slide 9 — Results, limitations, and testing

- 2,404 inventory units; 9,277 requested; 7,055 supplied; 2,222 pending.
- Weighted fulfillment: 76.05%; simplified group shortfall: 372 units.
- Positive estimates: O+ 196, A+ 121, B+ 55 units.
- Synthetic, small dataset; no expiry, clinical allocation, or real-world inference.
- Latest suite: 19 tests passed; compileall completed successfully.

**Speaker notes:** These results come from the current cleaned synthetic CSVs. Explain that real database values can differ if records have been changed. Point out that tests include preprocessing, CRUD validation, analytics, and a Streamlit smoke test.

## Slide 10 — Conclusion and future scope

- Demonstrates a reproducible data-to-dashboard workflow with MongoDB and Python.
- Helps inspect selected inventory, demand, donation patterns, and data quality.
- Future: approved real data, expiry/component modelling, security, and separately validated forecasting.
- Further deployment or Atlas evidence requires separate configuration and verification.

**Speaker notes:** Close by repeating that the system is an academic analytics prototype. Forecasting, clinical decision support, and Atlas deployment are future work, not current capabilities.
