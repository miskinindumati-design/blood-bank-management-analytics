# Blood Bank Management Analytics Using MongoDB

This project is a college-level Big Data Analytics mini project focused on synthetic blood inventory monitoring, hospital request and fulfillment analysis, and donation trends using MongoDB, Python, Pandas, and Streamlit. It does not currently implement forecasting or clinical allocation.

## Features

- Synthetic, deterministic blood bank and hospital dataset generation.
- Data cleaning and validation pipeline with summary statistics.
- MongoDB integration using PyMongo for the configured endpoint (the verified setup is local MongoDB; Atlas has not been tested).
- Validated CRUD operations for inventory and hospital request records, with confirmed deletes.
- MongoDB aggregation pipelines for inventory totals, donation trends, and hospital demand.
- Analytics for shortage detection, donation trends, and fulfillment performance.
- Daily, weekly, and monthly donation trends; donation breakdowns; descriptive statistics; configurable low-stock alerts.
- Interactive Plotly dashboard in Streamlit.
- Reproducible CSV exports for demonstration and viva preparation.

## Project structure

- `src/data_generation.py` — dataset generation and cleaning pipeline
- `src/db/connection.py` — MongoDB connection helper
- `src/db/seed.py` — database initialization and seeding
- `src/db/repository.py` — validation, CRUD, indexes, and aggregation pipelines
- `src/analytics.py` — analytics calculations
- `src/app.py` — Streamlit dashboard
- `data/raw/` — raw CSV files
- `data/cleaned/` — cleaned CSV files
- `docs/project_report.md` — full project report
- `docs/database_schema.md` — schema and sample documents
- `docs/presentation_outline.md` — 10-slide outline and speaker notes
- `docs/viva_questions.md` — viva question bank and sample answers
- `docs/demo_script.md` — timed live demonstration script
- `docs/screenshots_checklist.md` — dashboard and local MongoDB evidence checklist
- `docs/demo_viva_guide.md` — setup and links to presentation/demo materials

## Quick start

1. Create a virtual environment and install requirements:

   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Generate synthetic data and clean it:

   python3 -m src.data_generation

3. Configure MongoDB credentials in a `.env` file:

   MONGODB_URI=mongodb://localhost:27017
   MONGODB_DB=blood_bank_analytics

4. Seed the database:

   python3 -m src.db.seed

5. Launch the dashboard:

   streamlit run src/app.py

## Notes

- The project is designed to work with a live MongoDB deployment if available.
- When MongoDB is not configured, the dashboard automatically falls back to the cleaned CSV files for demonstration.
- MongoDB validation in this workspace confirmed a local `localhost` database only; Atlas connectivity has not been verified.
- Seeding is additive: it inserts missing identifiers without replacing or deleting existing documents.
- Synthetic data is deterministic, so the numbers are reproducible.
