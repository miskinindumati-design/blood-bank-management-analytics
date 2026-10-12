# Five-Minute Live Demonstration Script

## Before the demonstration

1. Open the project directory in a terminal and activate the project's virtual environment.
2. Start the app with `streamlit run src/app.py`, then open the URL printed by Streamlit.
3. Confirm the dashboard loads without an exception. If the app reports CSV fallback, explain that it is read-only and skip the database CRUD segment.
4. For the CRUD demonstration, use only a development/local database. Do not edit or delete an existing inventory record. Check that the unique demo ID below is not already present before creating it.
5. Keep `.env`, MongoDB connection strings, and credentials out of screenshots and screen sharing.

## Timed demonstration

### 0:00–0:30 — Introduce the project

- Show the dashboard title and explain that the dataset is deterministic synthetic data.
- State: “This is an academic analytics prototype, not a clinical allocation system.”
- Point out any MongoDB connection status or CSV fallback warning.

### 0:30–1:10 — Show filters and headline KPIs

- In the left sidebar, point to **Start date**, **End date**, **Blood group**, **Hospital**, **Location**, **Blood bank**, and **Low-stock alert threshold (units)**.
- Leave all categorical filters at **All** and use the default full date range.
- Read the KPI labels: inventory, hospital demand, supplied, pending, weighted fulfillment, estimated shortage.
- Explain weighted fulfillment: total supplied units divided by total requested units, multiplied by 100.

### 1:10–2:15 — Explain inventory and demand

- Open the **Inventory** results tab.
- Show **Inventory by blood group**, the percentage table, inventory-by-bank chart, and low-stock alerts.
- Explain that the threshold is applied to each bank/group inventory row.
- Open **Hospital demand**.
- Show requested, supplied, and pending units by hospital, then weighted fulfillment by hospital.
- Show the blood-group demand/shortage comparison and explain that different groups are calculated separately.

### 2:15–3:00 — Show donation trends and findings

- Open **Donation trends**.
- Show **Daily**, **Weekly**, and **Monthly** in turn; explain that weeks begin on Monday.
- Show donation breakdown tabs for blood group, blood bank, and location.
- Open **Findings and statistics** to show top hospitals, greatest estimated shortages, and the mean/median/minimum/maximum/sample-standard-deviation table.
- State that shortage is a simplified estimate, not a clinical recommendation.

### 3:00–4:30 — Demonstrate a safe inventory create and update

Perform this only against a development/local MongoDB database:

1. Scroll below the analytical results to **MongoDB inventory and request management**.
2. Open the **Inventory CRUD** tab. Check the existing inventory IDs first. If `INV-DEMO-PHASE4-20261012-01` already exists, choose a different unique ID.
3. Under **Create inventory record**, enter the unique demo ID, select a bank, select **O+**, enter **5** available units, and set the inventory update date to **2025-06-30** so it falls within the default dashboard range.
4. Select **Create inventory**. Point out the success message and that the refreshed dashboard reflects the additional record.
5. Under **Update inventory record**, select only the new `INV-DEMO-...` record, change available units from **5** to **6**, and select **Save inventory update**.
6. Explain that the change is persisted to MongoDB, then clean up only the temporary demo record using the delete form: select the same `INV-DEMO-...` ID, tick **I confirm deletion of this inventory record**, and select **Delete inventory record**.
7. Confirm the success message. Never select a pre-existing inventory ID for deletion. If cleanup fails, record the demo ID and remove only that exact test record after the demo.

If this is not a disposable development database or you do not have permission to write, do not perform CRUD live; show the form and explain the validation and confirmation instead.

### 4:30–5:00 — Export and close

- Return to the analytics area and select **Download selected analytical results (ZIP)**.
- Summarize one finding from the full synthetic data, such as the **76.05%** overall weighted fulfillment or the group-level estimates (**O+ 196, A+ 121, B+ 55**).
- Close with limitations: synthetic sample, simplified estimate, no clinical allocation, and local MongoDB verification only.

## Short closing statement

“The project demonstrates repeatable synthetic-data preprocessing, MongoDB document operations, and filterable analytics in Streamlit. It supports review and discussion, but it is not a production clinical system.”
