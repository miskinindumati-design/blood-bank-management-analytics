# Screenshots Checklist for Final Submission

Capture genuine screenshots from the running application and the local MongoDB database. Do not recreate charts, edit values into images, or present synthetic screenshots as live MongoDB evidence. Use the same app/data state as the report where possible, and note any changed/demo data.

## Streamlit dashboard

- [ ] **Dashboard overview:** title, sidebar filters, data-source status, and headline KPIs visible together.
- [ ] **Inventory analysis:** inventory by blood group, percentage table, and inventory by blood bank.
- [ ] **Low-stock alerts:** configurable threshold visible with the resulting records/table.
- [ ] **Hospital demand:** requested, supplied, pending units, and weighted fulfillment chart/table.
- [ ] **Group shortage analysis:** demand, stock, and simplified estimated-shortage view with its limitation caption visible.
- [ ] **Donation trends:** capture daily, weekly, and monthly trend tabs (one screenshot per period if necessary).
- [ ] **Donation breakdowns:** at least one blood-group chart and the blood-bank/location views.
- [ ] **Findings and statistics:** top hospitals, greatest shortages, and descriptive-statistics table.
- [ ] **Export control:** selected analytical-results ZIP download control visible; optionally show the downloaded CSV filenames without exposing unrelated personal files.
- [ ] **CRUD update:** only if using a permitted development database, show the dedicated `INV-DEMO-...` record and successful update; capture cleanup confirmation/success as appropriate. Do not show or delete unrelated records.

## Local MongoDB evidence

- [ ] **Database and collections:** MongoDB Compass or an equivalent client showing `blood_bank_analytics` and the five collection names: `blood_banks`, `hospitals`, `blood_inventory`, `donations`, and `hospital_requests`.
- [ ] **Sample documents:** show representative bank, hospital, inventory, donation, and request documents. Keep the capture limited to what is needed for the academic demonstration.
- [ ] **Indexes or validation:** optionally show a unique identifier index and the inventory/request document validator configuration.
- [ ] **Aggregation evidence:** optionally show one actual aggregation result, such as monthly donation totals or hospital demand grouped in MongoDB.
- [ ] **CRUD persistence evidence:** if performed, show the temporary inventory record after the update and its removal after cleanup; include no unrelated records.

## Privacy and evidence quality

- [ ] Verify screenshots come from the actual dashboard/database session; do not imply Atlas evidence when using local MongoDB.
- [ ] Hide `.env`, shell history, connection strings, credentials, tokens, and irrelevant database details.
- [ ] Keep browser tabs and desktop notifications unrelated to the project out of the capture.
- [ ] Use readable zoom and include chart/table titles and filter context.
- [ ] Label project-generated data as synthetic if that context is not already visible.
- [ ] Save the original captures in the college-required format/location and use consistent, descriptive filenames.

Screenshots are not included by this checklist; capture them during the actual final demo.
