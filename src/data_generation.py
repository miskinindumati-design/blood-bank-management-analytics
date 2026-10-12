from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import CLEAN_DIR, RAW_DIR

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
BLOOD_BANKS = [
    {"bank_id": "BB-101", "bank_name": "Lifeline Blood Bank", "location": "Bengaluru", "city": "Bengaluru", "contact": "+91-80-000-1001"},
    {"bank_id": "BB-202", "bank_name": "Mercy Blood Centre", "location": "Mysuru", "city": "Mysuru", "contact": "+91-82-000-2002"},
    {"bank_id": "BB-303", "bank_name": "CarePlus Blood Bank", "location": "Hubballi", "city": "Hubballi", "contact": "+91-83-000-3003"},
]
HOSPITALS = [
    {"hospital_id": "H-01", "hospital_name": "CityCare General Hospital", "location": "Bengaluru", "city": "Bengaluru"},
    {"hospital_id": "H-02", "hospital_name": "Green Valley Hospital", "location": "Mysuru", "city": "Mysuru"},
    {"hospital_id": "H-03", "hospital_name": "Metro Trauma Center", "location": "Hubballi", "city": "Hubballi"},
    {"hospital_id": "H-04", "hospital_name": "Rural Care Hospital", "location": "Bellary", "city": "Bellary"},
]


def generate_synthetic_datasets() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(42)

    banks_df = pd.DataFrame(BLOOD_BANKS)
    hospitals_df = pd.DataFrame(HOSPITALS)

    inventory_rows = []
    for bank in BLOOD_BANKS:
        for group in BLOOD_GROUPS:
            base = 75 + (BLOOD_GROUPS.index(group) * 8) + (int(bank["bank_id"].split("-")[-1]) % 5)
            available_units = int(max(18, base + rng.integers(-20, 18)))
            if group in {"AB-", "O-"}:
                available_units = max(12, available_units - 18)
            inventory_rows.append(
                {
                    "inventory_id": f"INV-{bank['bank_id']}-{group}",
                    "bank_id": bank["bank_id"],
                    "bank_name": bank["bank_name"],
                    "location": bank["location"],
                    "blood_group": group,
                    "available_units": available_units,
                    "last_updated": "2025-06-30",
                }
            )
    inventory_df = pd.DataFrame(inventory_rows)

    donation_rows = []
    start_date = pd.Timestamp("2024-01-01")
    end_date = pd.Timestamp("2025-06-30")
    for i in range(500):
        donor_age = int(rng.integers(18, 62))
        blood_group = rng.choice(BLOOD_GROUPS, p=np.array([0.18, 0.08, 0.17, 0.07, 0.09, 0.04, 0.24, 0.13]))
        bank = rng.choice(BLOOD_BANKS)
        donation_date = start_date + pd.to_timedelta(int(rng.integers(0, (end_date - start_date).days + 1)), unit="D")
        units = int(rng.integers(1, 4))
        donation_rows.append(
            {
                "donation_id": f"DON-{i + 1:04d}",
                "donor_age": donor_age,
                "blood_group": blood_group,
                "donation_units": units,
                "donation_date": donation_date.strftime("%Y-%m-%d"),
                "bank_id": bank["bank_id"],
                "bank_name": bank["bank_name"],
                "location": bank["location"],
                "donor_type": "voluntary" if i % 2 == 0 else "replacement",
                "status": "successful",
            }
        )
    donations_df = pd.DataFrame(donation_rows)

    request_rows = []
    for i in range(500):
        hospital = rng.choice(HOSPITALS)
        bank = rng.choice(BLOOD_BANKS)
        blood_group = rng.choice(BLOOD_GROUPS, p=np.array([0.18, 0.06, 0.15, 0.08, 0.11, 0.05, 0.24, 0.13]))
        requested_units = int(rng.integers(4, 32))
        if blood_group in {"AB-", "O-"}:
            requested_units = int(rng.integers(6, 38))
        request_date = start_date + pd.to_timedelta(int(rng.integers(0, (end_date - start_date).days + 1)), unit="D")
        fulfillment_ratio = 0.55 + rng.random() * 0.45
        supplied_units = int(round(requested_units * fulfillment_ratio))
        if requested_units < 10:
            supplied_units = min(requested_units, int(rng.integers(0, requested_units + 1)))
        pending_units = max(requested_units - supplied_units, 0)
        fulfillment_percentage = round((supplied_units / requested_units) * 100, 2) if requested_units else 0.0
        request_rows.append(
            {
                "request_id": f"REQ-{i + 1:04d}",
                "hospital_id": hospital["hospital_id"],
                "hospital_name": hospital["hospital_name"],
                "location": hospital["location"],
                "blood_group": blood_group,
                "bank_id": bank["bank_id"],
                "bank_name": bank["bank_name"],
                "requested_units": requested_units,
                "supplied_units": supplied_units,
                "pending_units": pending_units,
                "fulfillment_percentage": fulfillment_percentage,
                "request_date": request_date.strftime("%Y-%m-%d"),
                "priority": "urgent" if i % 5 == 0 else "normal",
                "status": "fulfilled" if pending_units == 0 else ("partial" if supplied_units > 0 else "pending"),
            }
        )
    requests_df = pd.DataFrame(request_rows)

    return {
        "blood_banks": banks_df,
        "hospitals": hospitals_df,
        "blood_inventory": inventory_df,
        "donations": donations_df,
        "hospital_requests": requests_df,
    }


def preprocess_datasets(
    raw_data: dict[str, pd.DataFrame] | None = None,
) -> dict[str, object]:
    """Validate all records, retaining rejected-row reasons in the result."""
    source = generate_synthetic_datasets() if raw_data is None else raw_data
    cleaned: dict[str, pd.DataFrame] = {}
    issues: list[dict[str, object]] = []
    id_fields = {
        "blood_banks": "bank_id",
        "hospitals": "hospital_id",
        "blood_inventory": "inventory_id",
        "donations": "donation_id",
        "hospital_requests": "request_id",
    }
    required_fields = {
        "blood_banks": set(BLOOD_BANKS[0]),
        "hospitals": set(HOSPITALS[0]),
        "blood_inventory": {
            "inventory_id", "bank_id", "bank_name", "location", "blood_group",
            "available_units", "last_updated",
        },
        "donations": {
            "donation_id", "donor_age", "blood_group", "donation_units",
            "donation_date", "bank_id", "bank_name", "location", "donor_type",
            "status",
        },
        "hospital_requests": {
            "request_id", "hospital_id", "hospital_name", "location",
            "blood_group", "bank_id", "bank_name", "requested_units",
            "supplied_units", "pending_units", "fulfillment_percentage",
            "request_date", "priority", "status",
        },
    }
    banks_frame = source["blood_banks"]
    hospitals_frame = source["hospitals"]
    banks = (
        banks_frame.dropna(subset=["bank_id"])
        .drop_duplicates("bank_id")
        .set_index("bank_id")
        .to_dict("index")
        if {"bank_id", "bank_name", "location"}.issubset(banks_frame.columns)
        else {}
    )
    hospitals = (
        hospitals_frame.dropna(subset=["hospital_id"])
        .drop_duplicates("hospital_id")
        .set_index("hospital_id")
        .to_dict("index")
        if {"hospital_id", "hospital_name", "location"}.issubset(hospitals_frame.columns)
        else {}
    )
    bank_ids = set(banks)
    hospital_ids = set(hospitals)
    summaries: dict[str, dict[str, int]] = {}
    duplicate_total = 0

    for name, frame in source.items():
        id_field = id_fields[name]
        missing_columns = required_fields[name] - set(frame.columns)
        if missing_columns:
            issues.append(
                {
                    "dataset": name,
                    "row": 0,
                    "id": None,
                    "reasons": [
                        f"missing required column: {field}"
                        for field in sorted(missing_columns)
                    ],
                }
            )
        full_duplicates = set(frame.index[frame.duplicated(keep="first")])
        duplicate_ids = (
            set(frame.loc[frame[id_field].duplicated(keep=False), id_field].dropna())
            if id_field in frame
            else set()
        )
        duplicate_total += len(full_duplicates)
        valid_indices: list[int] = []

        for index, row in frame.iterrows():
            errors: list[str] = []
            if index in full_duplicates:
                errors.append("duplicate full record")
            for field in required_fields[name]:
                if field not in frame.columns or pd.isna(row.get(field)):
                    errors.append(f"missing required field: {field}")
                elif isinstance(row.get(field), str) and not row[field].strip():
                    errors.append(f"empty required field: {field}")

            record_id = row.get(id_field)
            if pd.notna(record_id):
                if not isinstance(record_id, str) or not record_id.strip():
                    errors.append(f"{id_field} must be a non-empty string")
                if record_id in duplicate_ids:
                    errors.append(f"duplicate identifier: {id_field}={record_id}")

            if name in {"blood_inventory", "donations", "hospital_requests"}:
                if pd.notna(row.get("blood_group")) and row.get("blood_group") not in BLOOD_GROUPS:
                    errors.append("invalid blood group")
                bank_id = row.get("bank_id")
                if pd.notna(bank_id) and bank_id not in bank_ids:
                    errors.append("unknown blood bank reference")
                elif pd.notna(bank_id):
                    bank = banks[bank_id]
                    if row.get("bank_name") != bank["bank_name"]:
                        errors.append("blood bank name does not match reference")
                    if name != "hospital_requests" and row.get("location") != bank["location"]:
                        errors.append("location does not match blood bank reference")

            if name == "blood_inventory":
                try:
                    units = float(row["available_units"])
                    if not units.is_integer() or units < 0:
                        errors.append("available_units must be a non-negative integer")
                except (KeyError, TypeError, ValueError):
                    errors.append("available_units must be numeric")

            if name == "donations":
                try:
                    age = float(row["donor_age"])
                    units = float(row["donation_units"])
                    if not age.is_integer() or not 18 <= age <= 65:
                        errors.append("donor_age must be an integer from 18 to 65")
                    if not units.is_integer() or units <= 0:
                        errors.append("donation_units must be a positive integer")
                except (KeyError, TypeError, ValueError):
                    errors.append("donor_age and donation_units must be numeric")
                if row.get("donor_type") not in {"voluntary", "replacement"}:
                    errors.append("donor_type must be voluntary or replacement")
                if row.get("status") != "successful":
                    errors.append("donation status must be successful")

            if name == "hospital_requests":
                hospital_id = row.get("hospital_id")
                if pd.notna(hospital_id) and hospital_id not in hospital_ids:
                    errors.append("unknown hospital reference")
                elif pd.notna(hospital_id):
                    hospital = hospitals[hospital_id]
                    if row.get("hospital_name") != hospital["hospital_name"] or row.get("location") != hospital["location"]:
                        errors.append("hospital name or location does not match reference")
                try:
                    requested = float(row["requested_units"])
                    supplied = float(row["supplied_units"])
                    pending = float(row["pending_units"])
                    fulfillment = float(row["fulfillment_percentage"])
                    if not requested.is_integer() or requested <= 0:
                        errors.append("requested_units must be a positive integer")
                    if not supplied.is_integer() or supplied < 0 or supplied > requested:
                        errors.append("supplied_units must be from zero to requested_units")
                    if pending != max(requested - supplied, 0):
                        errors.append("pending_units is inconsistent")
                    expected_pct = round(supplied / requested * 100, 2) if requested else 0
                    if fulfillment != expected_pct:
                        errors.append("fulfillment_percentage is inconsistent")
                    expected_status = "fulfilled" if pending == 0 else ("partial" if supplied > 0 else "pending")
                    if row.get("status") != expected_status:
                        errors.append("request status is inconsistent")
                except (KeyError, TypeError, ValueError, ZeroDivisionError):
                    errors.append("request units and fulfillment must be numeric")
                if row.get("priority") not in {"normal", "urgent"}:
                    errors.append("priority must be normal or urgent")

            date_field = {
                "blood_inventory": "last_updated",
                "donations": "donation_date",
                "hospital_requests": "request_date",
            }.get(name)
            if date_field:
                if pd.isna(pd.to_datetime(row.get(date_field), errors="coerce")):
                    errors.append(f"invalid date: {date_field}")

            if errors:
                issues.append(
                    {
                        "dataset": name,
                        "row": int(index) + 2,
                        "id": record_id,
                        "reasons": errors,
                    }
                )
            else:
                valid_indices.append(index)

        clean_frame = frame.loc[valid_indices].copy()
        date_field = {
            "blood_inventory": "last_updated",
            "donations": "donation_date",
            "hospital_requests": "request_date",
        }.get(name)
        if date_field:
            if date_field in clean_frame:
                clean_frame[date_field] = pd.to_datetime(clean_frame[date_field], errors="raise")
        for numeric_field in {
            "blood_inventory": ("available_units",),
            "donations": ("donor_age", "donation_units"),
            "hospital_requests": (
                "requested_units", "supplied_units", "pending_units",
                "fulfillment_percentage",
            ),
        }.get(name, ()):
            if numeric_field in clean_frame:
                clean_frame[numeric_field] = pd.to_numeric(clean_frame[numeric_field], errors="raise")

        cleaned[name] = clean_frame.reset_index(drop=True)
        summaries[name] = {
            "before": len(frame),
            "after": len(cleaned[name]),
            "removed": len(frame) - len(cleaned[name]),
            "duplicate_records": int(frame.duplicated().sum()),
            "missing_cells": int(frame.isna().sum().sum()),
            "invalid_records": sum(issue["dataset"] == name for issue in issues),
        }

    return {
        "raw": source,
        "cleaned": cleaned,
        "summary": summaries,
        "issues": issues,
        "duplicate_records": duplicate_total,
    }


def clean_and_save_datasets(
    raw_data: dict[str, pd.DataFrame] | None = None,
) -> dict[str, object]:
    result = preprocess_datasets(raw_data)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    for name, df in result["raw"].items():
        path_raw = RAW_DIR / f"{name}.csv"
        df.to_csv(path_raw, index=False)

    for name, cleaned in result["cleaned"].items():
        path_clean = CLEAN_DIR / f"{name}.csv"
        cleaned.to_csv(path_clean, index=False)

    return result


def main() -> None:
    result = clean_and_save_datasets()
    for name, values in result["summary"].items():
        print(
            f"{name}: before={values['before']} after={values['after']} "
            f"removed={values['removed']} duplicates={values['duplicate_records']} "
            f"missing_cells={values['missing_cells']} invalid={values['invalid_records']}"
        )
    for issue in result["issues"]:
        print(
            f"Rejected {issue['dataset']} row {issue['row']} (id={issue['id']}): "
            f"{'; '.join(issue['reasons'])}"
        )


if __name__ == "__main__":
    main()
