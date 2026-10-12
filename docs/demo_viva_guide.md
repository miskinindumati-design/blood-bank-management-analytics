# Demo and Viva Guide

This file is the short navigation page for final presentation materials. Use the linked documents as the source of truth to avoid maintaining duplicate scripts and question lists:

- [Project report](./project_report.md) — academic report, verified calculations, methods, limitations, and references.
- [10-slide presentation outline](./presentation_outline.md) — slide bullets and speaker notes.
- [Viva questions and answers](./viva_questions.md) — beginner-friendly questions across the project topics.
- [Five-minute live demo script](./demo_script.md) — timed dashboard navigation and safe, temporary inventory CRUD demonstration.
- [Screenshot checklist](./screenshots_checklist.md) — dashboard and local MongoDB evidence to capture.
- [Database schema](./database_schema.md) — collections, sample documents, identifiers, validators, and aggregations.

## Run the project for a demonstration

From the project root, activate the virtual environment and install dependencies if needed:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Generate and validate the reproducible CSV data:

```bash
python3 -m src.data_generation
```

For MongoDB-backed reads and CRUD, configure `MONGODB_URI` and `MONGODB_DB` in the local environment, ensure the MongoDB service is available, and seed additively if required:

```bash
python3 -m src.db.seed
```

Seeding inserts missing IDs and does not reset or replace matching existing records. The verified setup is local MongoDB; Atlas connectivity has not been tested. If MongoDB is unavailable, the dashboard can run from cleaned CSV files in read-only mode.

Start Streamlit:

```bash
streamlit run src/app.py
```

Before demonstrating a CRUD write, use a development database and follow the temporary-record/cleanup instructions in [demo_script.md](./demo_script.md). Never use an existing record as the deletion test target.
