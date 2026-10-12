from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.analytics import (
    analytics_export_zip,
    filter_analytics_frame,
    get_analytics_results,
    get_donation_trend,
    get_donation_period_trend,
    get_shortage_by_blood_group,
    get_summary_metrics,
)
from src.data_generation import (
    BLOOD_GROUPS,
    generate_synthetic_datasets,
    preprocess_datasets,
)
from src.db.repository import (
    ValidationError,
    create_hospital_request,
    create_inventory,
    donation_trends_pipeline,
    delete_hospital_request,
    delete_inventory,
    hospital_demand_pipeline,
    update_hospital_request,
    update_inventory,
)


class MemoryCollection:
    def __init__(self, documents: list[dict] | None = None) -> None:
        self.documents = documents or []

    def find_one(self, query: dict) -> dict | None:
        return next(
            (
                document
                for document in self.documents
                if all(document.get(key) == value for key, value in query.items())
            ),
            None,
        )

    def insert_one(self, document: dict) -> None:
        if self.find_one({"_id": document["_id"]}) is not None:
            from pymongo.errors import DuplicateKeyError

            raise DuplicateKeyError("duplicate")
        self.documents.append(document.copy())

    def update_one(self, query: dict, update: dict) -> SimpleNamespace:
        document = self.find_one(query)
        if document is None:
            return SimpleNamespace(matched_count=0)
        document.update(update["$set"])
        return SimpleNamespace(matched_count=1)

    def delete_one(self, query: dict) -> SimpleNamespace:
        document = self.find_one(query)
        if document is None:
            return SimpleNamespace(deleted_count=0)
        self.documents.remove(document)
        return SimpleNamespace(deleted_count=1)


class MemoryDatabase:
    def __init__(self) -> None:
        self.collections = {
            "blood_banks": MemoryCollection(
                [
                    {
                        "bank_id": "BB-101",
                        "bank_name": "Lifeline Blood Bank",
                        "location": "Bengaluru",
                    }
                ]
            ),
            "hospitals": MemoryCollection(
                [
                    {
                        "hospital_id": "H-01",
                        "hospital_name": "CityCare General Hospital",
                        "location": "Bengaluru",
                    }
                ]
            ),
            "blood_inventory": MemoryCollection(),
            "hospital_requests": MemoryCollection(),
        }

    def __getitem__(self, name: str) -> MemoryCollection:
        return self.collections[name]


def test_blood_group_coverage() -> None:
    result = generate_synthetic_datasets()
    inventory = result["blood_inventory"]
    assert set(BLOOD_GROUPS) == set(inventory["blood_group"].unique())
    assert inventory.shape[0] == 24


def test_record_counts() -> None:
    result = generate_synthetic_datasets()
    assert result["donations"].shape[0] == 500
    assert result["hospital_requests"].shape[0] == 500
    assert result["blood_banks"].shape[0] == 3
    assert result["hospitals"].shape[0] == 4


def test_positive_units() -> None:
    result = generate_synthetic_datasets()
    assert (result["donations"]["donation_units"] > 0).all()
    assert (result["hospital_requests"]["requested_units"] > 0).all()
    assert (result["blood_inventory"]["available_units"] > 0).all()


def test_csv_preprocessing_summary_shapes() -> None:
    inventory = pd.read_csv("data/cleaned/blood_inventory.csv")
    requests = pd.read_csv("data/cleaned/hospital_requests.csv")
    donations = pd.read_csv("data/cleaned/donations.csv")
    result = preprocess_datasets()

    assert inventory.shape[0] >= 24
    assert requests.shape[0] >= 500
    assert donations.shape[0] >= 500
    assert all(summary["removed"] == 0 for summary in result["summary"].values())
    assert all(summary["invalid_records"] == 0 for summary in result["summary"].values())


def test_donation_trend_groups_and_sorts_dates() -> None:
    donations = pd.DataFrame(
        {
            "donation_date": ["2025-01-02", "2025-01-01", "2025-01-02"],
            "donation_units": [2, 1, 3],
        }
    )

    trend = get_donation_trend(donations)

    assert list(trend.columns) == ["date", "donation_units"]
    assert trend["date"].tolist() == [
        pd.Timestamp("2025-01-01"),
        pd.Timestamp("2025-01-02"),
    ]
    assert trend["donation_units"].tolist() == [1, 5]


def test_shortage_is_calculated_by_blood_group() -> None:
    inventory = pd.DataFrame(
        {
            "blood_group": ["O+", "A+", "B+", "AB+"],
            "available_units": [100, 100, 100, 100],
        }
    )
    requests = pd.DataFrame(
        {
            "blood_group": ["O+", "A+", "B+", "AB+"],
            "pending_units": [296, 221, 155, 40],
        }
    )

    shortages = get_shortage_by_blood_group(inventory, requests).set_index("blood_group")

    assert shortages["potential_shortage"].to_dict() == {
        "A+": 121,
        "AB+": 0,
        "B+": 55,
        "O+": 196,
    }


def test_shortage_handles_empty_filtered_data() -> None:
    shortages = get_shortage_by_blood_group(pd.DataFrame(), pd.DataFrame())

    assert list(shortages.columns) == [
        "blood_group",
        "available_units",
        "pending_units",
        "potential_shortage",
    ]
    assert shortages.empty


def test_summary_metrics_use_supplied_frames_and_weighted_fulfillment() -> None:
    inventory = pd.DataFrame(
        {"blood_group": ["O+"], "available_units": [10]}
    )
    donations = pd.DataFrame(
        {"donation_units": [2], "donation_date": ["2025-01-01"]}
    )
    requests = pd.DataFrame(
        {
            "blood_group": ["O+", "A+"],
            "requested_units": [100, 30],
            "supplied_units": [90, 15],
            "pending_units": [10, 15],
            "hospital_name": ["Hospital 1", "Hospital 1"],
        }
    )

    metrics = get_summary_metrics(inventory, donations, requests)

    assert metrics["total_available"] == 10
    assert metrics["total_donations"] == 2
    assert metrics["total_requested"] == 130
    assert metrics["total_supplied"] == 105
    assert metrics["potential_shortage"] == 15
    assert metrics["overall_fulfillment_percentage"] == 80.77


def test_streamlit_app_starts_without_exceptions() -> None:
    app_path = Path(__file__).resolve().parents[1] / "src" / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=30).run()

    assert not app.exception, "\n".join(error.message for error in app.exception)


def test_preprocessing_rejects_invalid_records_and_reports_counts() -> None:
    raw = generate_synthetic_datasets()
    raw = {name: frame.copy() for name, frame in raw.items()}
    raw["hospital_requests"].loc[0, "supplied_units"] = (
        raw["hospital_requests"].loc[0, "requested_units"] + 1
    )
    raw["hospital_requests"].loc[1, "hospital_id"] = "UNKNOWN"
    raw["donations"].loc[0, "blood_group"] = "X+"
    raw["donations"]["donation_id"] = raw["donations"]["donation_id"].astype(object)
    raw["donations"].loc[1, "donation_id"] = 2
    raw["blood_inventory"].loc[0, "last_updated"] = "not-a-date"
    raw["blood_banks"].loc[0, "contact"] = None

    result = preprocess_datasets(raw)
    issue_text = " ".join(
        reason for issue in result["issues"] for reason in issue["reasons"]
    )

    assert result["summary"]["hospital_requests"]["before"] == 500
    assert result["summary"]["hospital_requests"]["after"] == 498
    assert result["summary"]["blood_inventory"]["after"] == 23
    assert result["summary"]["donations"]["after"] == 498
    assert "supplied_units must be from zero to requested_units" in issue_text
    assert "unknown hospital reference" in issue_text
    assert "invalid blood group" in issue_text
    assert "donation_id must be a non-empty string" in issue_text
    assert "invalid date: last_updated" in issue_text
    assert "missing required field: contact" in issue_text


def test_preprocessing_detects_duplicate_rows_and_identifiers() -> None:
    raw = generate_synthetic_datasets()
    raw = {name: frame.copy() for name, frame in raw.items()}
    duplicate = raw["donations"].iloc[[0]].copy()
    raw["donations"] = pd.concat([raw["donations"], duplicate], ignore_index=True)
    same_id = raw["donations"].iloc[1].copy()
    same_id["donation_id"] = raw["donations"].iloc[0]["donation_id"]
    raw["donations"] = pd.concat(
        [raw["donations"], same_id.to_frame().T], ignore_index=True
    )

    result = preprocess_datasets(raw)
    reasons = [
        reason
        for issue in result["issues"]
        for reason in issue["reasons"]
    ]

    assert result["summary"]["donations"]["before"] == 502
    assert result["summary"]["donations"]["after"] == 499
    assert result["summary"]["donations"]["duplicate_records"] == 1
    assert any("duplicate identifier: donation_id" in reason for reason in reasons)


def test_inventory_and_request_crud_validates_and_persists_changes() -> None:
    database = MemoryDatabase()
    inventory_id = create_inventory(
        database,
        {
            "inventory_id": "INV-TEST-1",
            "bank_id": "BB-101",
            "blood_group": "A+",
            "available_units": 12,
            "last_updated": "2025-06-30",
        },
    )
    update_inventory(
        database,
        inventory_id,
        available_units=18,
        last_updated="2025-07-01",
    )
    assert database["blood_inventory"].find_one({"inventory_id": inventory_id})[
        "available_units"
    ] == 18
    with pytest.raises(ValidationError, match="inventory ID already exists"):
        create_inventory(
            database,
            {
                "inventory_id": inventory_id,
                "bank_id": "BB-101",
                "blood_group": "A+",
                "available_units": 9,
                "last_updated": "2025-06-30",
            },
        )

    with pytest.raises(ValidationError, match="Supplied units cannot exceed"):
        create_hospital_request(
            database,
            {
                "request_id": "REQ-TEST-1",
                "hospital_id": "H-01",
                "bank_id": "BB-101",
                "blood_group": "O+",
                "requested_units": 4,
                "supplied_units": 5,
                "request_date": "2025-06-30",
            },
        )

    with pytest.raises(ValidationError, match="blood bank does not exist"):
        create_inventory(
            database,
            {
                "inventory_id": "INV-TEST-INVALID",
                "bank_id": "UNKNOWN",
                "blood_group": "A+",
                "available_units": 12,
                "last_updated": "2025-06-30",
            },
        )
    with pytest.raises(ValidationError, match="at least 0"):
        update_inventory(
            database,
            inventory_id,
            available_units=-1,
            last_updated="2025-07-01",
        )

    request_id = create_hospital_request(
        database,
        {
            "request_id": "REQ-TEST-1",
            "hospital_id": "H-01",
            "bank_id": "BB-101",
            "blood_group": "O+",
            "requested_units": 10,
            "supplied_units": 6,
            "request_date": "2025-06-30",
        },
    )
    update_hospital_request(
        database,
        request_id,
        requested_units=12,
        supplied_units=8,
        priority="urgent",
    )
    saved_request = database["hospital_requests"].find_one({"request_id": request_id})
    assert saved_request["pending_units"] == 4
    assert saved_request["fulfillment_percentage"] == 66.67
    assert saved_request["status"] == "partial"
    with pytest.raises(ValidationError, match="Supplied units cannot exceed"):
        update_hospital_request(
            database,
            request_id,
            requested_units=5,
            supplied_units=6,
            priority="urgent",
        )

    with pytest.raises(ValidationError, match="Confirm deletion"):
        delete_inventory(database, inventory_id, confirmed=False)
    with pytest.raises(ValidationError, match="Confirm deletion"):
        delete_hospital_request(database, request_id, confirmed=False)
    delete_inventory(database, inventory_id, confirmed=True)
    delete_hospital_request(database, request_id, confirmed=True)
    assert database["blood_inventory"].find_one({"inventory_id": inventory_id}) is None
    assert database["hospital_requests"].find_one({"request_id": request_id}) is None


def test_mongodb_pipelines_include_relevant_dashboard_filters() -> None:
    filters = {
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "blood_group": "O+",
        "hospital": "CityCare General Hospital",
        "location": "Bengaluru",
        "blood_bank": "Lifeline Blood Bank",
    }

    donation_match = donation_trends_pipeline(filters)[0]["$match"]
    request_match = hospital_demand_pipeline(filters)[0]["$match"]

    assert donation_match["blood_group"] == "O+"
    assert donation_match["bank_name"] == "Lifeline Blood Bank"
    assert donation_match["donation_date"]["$gte"].date().isoformat() == "2025-01-01"
    assert request_match["hospital_name"] == "CityCare General Hospital"
    assert request_match["request_date"]["$lt"].date().isoformat() == "2025-02-01"


def test_analytics_filters_apply_inclusive_dates_and_categories() -> None:
    donations = pd.DataFrame(
        {
            "donation_date": ["2025-01-01", "2025-01-15", "2025-02-01"],
            "blood_group": ["O+", "O+", "A+"],
            "bank_name": ["Bank A", "Bank B", "Bank A"],
            "location": ["North", "South", "North"],
            "donation_units": [1, 2, 3],
        }
    )
    filters = {
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "blood_group": "O+",
        "hospital": "All",
        "location": "North",
        "blood_bank": "Bank A",
    }

    result = filter_analytics_frame(donations, filters)

    assert result["donation_units"].tolist() == [1]
    assert result["donation_date"].tolist() == [pd.Timestamp("2025-01-01")]


def test_date_filter_is_applied_to_requests_and_inventory() -> None:
    filters = {
        "start_date": pd.Timestamp("2025-01-02"),
        "end_date": pd.Timestamp("2025-01-03"),
        "blood_group": "All",
        "hospital": "All",
        "location": "All",
        "blood_bank": "All",
    }
    requests = pd.DataFrame(
        {
            "request_date": ["2025-01-01", "2025-01-02", "2025-01-04"],
            "requested_units": [10, 20, 30],
        }
    )
    inventory = pd.DataFrame(
        {
            "last_updated": ["2025-01-01", "2025-01-03", "2025-01-04"],
            "available_units": [5, 10, 15],
        }
    )

    assert filter_analytics_frame(requests, filters)["requested_units"].tolist() == [
        20
    ]
    assert filter_analytics_frame(inventory, filters)[
        "available_units"
    ].tolist() == [10]


def test_donation_trends_support_day_week_and_month() -> None:
    donations = pd.DataFrame(
        {
            "donation_date": [
                "2025-01-05",
                "2025-01-06",
                "2025-01-31",
                "2025-02-01",
            ],
            "donation_units": [1, 2, 3, 4],
        }
    )

    daily = get_donation_period_trend(donations, "day")
    weekly = get_donation_period_trend(donations, "week")
    monthly = get_donation_period_trend(donations, "month")

    assert daily["donation_units"].sum() == 10
    assert weekly["donation_units"].sum() == 10
    assert weekly["period"].min() == pd.Timestamp("2024-12-30")
    assert monthly["period"].tolist() == [
        pd.Timestamp("2025-01-01"),
        pd.Timestamp("2025-02-01"),
    ]
    assert monthly["donation_units"].tolist() == [6, 4]


def test_analytics_results_calculate_weighted_fulfillment_and_group_shortages() -> None:
    inventory = pd.DataFrame(
        {
            "inventory_id": ["INV-1", "INV-2"],
            "bank_name": ["Bank A", "Bank A"],
            "location": ["North", "North"],
            "blood_group": ["O+", "A+"],
            "available_units": [10, 5],
            "last_updated": pd.to_datetime(["2025-01-31", "2025-01-31"]),
        }
    )
    donations = pd.DataFrame(
        {
            "donation_id": ["DON-1", "DON-2"],
            "donation_date": pd.to_datetime(["2025-01-01", "2025-01-02"]),
            "donation_units": [2, 3],
            "blood_group": ["O+", "O+"],
            "bank_name": ["Bank A", "Bank A"],
            "location": ["North", "North"],
        }
    )
    requests = pd.DataFrame(
        {
            "hospital_name": ["Hospital A", "Hospital B"],
            "blood_group": ["O+", "A+"],
            "requested_units": [100, 20],
            "supplied_units": [90, 10],
            "pending_units": [10, 10],
        }
    )

    results = get_analytics_results(inventory, donations, requests, 8)

    assert results["metrics"]["overall_fulfillment_percentage"] == 83.33
    assert results["metrics"]["total_requested"] == 120
    assert results["metrics"]["total_supplied"] == 100
    shortages = results["shortage_by_group"].set_index("blood_group")
    assert shortages["potential_shortage"].to_dict() == {"A+": 5, "O+": 0}
    assert results["low_stock"]["inventory_id"].tolist() == ["INV-2"]
    assert results["inventory_by_group"]["available_units"].sum() == results[
        "metrics"
    ]["total_available"]
    assert results["hospital_summary"]["requested_units"].sum() == results[
        "metrics"
    ]["total_requested"]
    assert results["hospital_summary"]["supplied_units"].sum() == results[
        "metrics"
    ]["total_supplied"]
    hospital_fulfillment = results["hospital_summary"].set_index("hospital_name")[
        "fulfillment_percentage"
    ]
    assert hospital_fulfillment.to_dict() == {
        "Hospital A": 90.0,
        "Hospital B": 50.0,
    }
    assert results["demand_by_group"]["pending_units"].sum() == results[
        "metrics"
    ]["total_pending"]
    assert results["donation_trends"]["month"]["donation_units"].sum() == results[
        "metrics"
    ]["total_donations"]
    assert results["donation_trends"]["day"]["donation_units"].sum() == results[
        "metrics"
    ]["total_donations"]
    assert results["donation_trends"]["week"]["donation_units"].sum() == results[
        "metrics"
    ]["total_donations"]
    assert results["donation_breakdowns"]["blood_group"][
        "donation_units"
    ].sum() == results["metrics"]["total_donations"]


def test_analytics_export_contains_selected_result_tables() -> None:
    results = get_analytics_results(
        pd.DataFrame({"blood_group": ["O+"], "available_units": [10]}),
        pd.DataFrame(
            {
                "donation_date": ["2025-01-01"],
                "donation_units": [2],
                "blood_group": ["O+"],
                "bank_name": ["Bank A"],
                "location": ["North"],
            }
        ),
        pd.DataFrame(
            {
                "hospital_name": ["Hospital A"],
                "blood_group": ["O+"],
                "requested_units": [10],
                "supplied_units": [8],
                "pending_units": [2],
            }
        ),
        low_stock_threshold=10,
    )

    from zipfile import ZipFile
    from io import BytesIO

    with ZipFile(BytesIO(analytics_export_zip(results))) as archive:
        filenames = set(archive.namelist())

    assert "inventory_by_blood_group.csv" in filenames
    assert "donation_trend_day.csv" in filenames
    assert "donations_by_location.csv" in filenames
    assert "shortage_by_blood_group.csv" in filenames
    assert "descriptive_statistics.csv" in filenames


def test_low_stock_threshold_must_be_non_negative() -> None:
    with pytest.raises(ValueError, match="must be non-negative"):
        get_analytics_results(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            low_stock_threshold=-1,
        )
