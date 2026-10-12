from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from pymongo import ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from src.data_generation import BLOOD_GROUPS


class ValidationError(ValueError):
    """Raised when a requested database operation violates project rules."""


def _parse_date(value: Any, field: str) -> datetime:
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a valid ISO date.") from None
    return parsed


def _validate_units(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise ValidationError(f"{field} must be an integer.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be an integer.") from None
    if parsed != value or parsed < minimum:
        raise ValidationError(f"{field} must be an integer of at least {minimum}.")
    return parsed


def _bank_reference(database: Database, bank_id: str) -> dict[str, Any]:
    bank = database["blood_banks"].find_one({"bank_id": bank_id})
    if bank is None:
        raise ValidationError("The selected blood bank does not exist.")
    return bank


def _hospital_reference(database: Database, hospital_id: str) -> dict[str, Any]:
    hospital = database["hospitals"].find_one({"hospital_id": hospital_id})
    if hospital is None:
        raise ValidationError("The selected hospital does not exist.")
    return hospital


def _make_inventory_document(database: Database, values: dict[str, Any]) -> dict[str, Any]:
    bank = _bank_reference(database, str(values.get("bank_id", "")))
    blood_group = values.get("blood_group")
    if blood_group not in BLOOD_GROUPS:
        raise ValidationError("Select a valid blood group.")
    inventory_id = str(values.get("inventory_id", "")).strip()
    if not inventory_id:
        raise ValidationError("Inventory ID is required.")
    return {
        "_id": inventory_id,
        "inventory_id": inventory_id,
        "bank_id": bank["bank_id"],
        "bank_name": bank["bank_name"],
        "location": bank["location"],
        "blood_group": blood_group,
        "available_units": _validate_units(values.get("available_units"), "Available units"),
        "last_updated": _parse_date(values.get("last_updated", datetime.now()), "Last updated"),
    }


def _make_request_document(database: Database, values: dict[str, Any]) -> dict[str, Any]:
    hospital = _hospital_reference(database, str(values.get("hospital_id", "")))
    bank = _bank_reference(database, str(values.get("bank_id", "")))
    blood_group = values.get("blood_group")
    if blood_group not in BLOOD_GROUPS:
        raise ValidationError("Select a valid blood group.")
    priority = values.get("priority", "normal")
    if priority not in {"normal", "urgent"}:
        raise ValidationError("Priority must be normal or urgent.")
    request_id = str(values.get("request_id", "")).strip()
    if not request_id:
        raise ValidationError("Request ID is required.")
    requested = _validate_units(values.get("requested_units"), "Requested units", minimum=1)
    supplied = _validate_units(values.get("supplied_units"), "Supplied units")
    if supplied > requested:
        raise ValidationError("Supplied units cannot exceed requested units.")
    pending = requested - supplied
    return {
        "_id": request_id,
        "request_id": request_id,
        "hospital_id": hospital["hospital_id"],
        "hospital_name": hospital["hospital_name"],
        "location": hospital["location"],
        "blood_group": blood_group,
        "bank_id": bank["bank_id"],
        "bank_name": bank["bank_name"],
        "requested_units": requested,
        "supplied_units": supplied,
        "pending_units": pending,
        "fulfillment_percentage": round(supplied / requested * 100, 2),
        "request_date": _parse_date(values.get("request_date", datetime.now()), "Request date"),
        "priority": priority,
        "status": "fulfilled" if pending == 0 else ("partial" if supplied > 0 else "pending"),
    }


def create_inventory(database: Database, values: dict[str, Any]) -> str:
    document = _make_inventory_document(database, values)
    try:
        database["blood_inventory"].insert_one(document)
    except DuplicateKeyError:
        raise ValidationError("That inventory ID already exists.") from None
    return document["inventory_id"]


def update_inventory(
    database: Database,
    inventory_id: str,
    *,
    available_units: Any,
    last_updated: Any,
) -> None:
    update = {
        "available_units": _validate_units(available_units, "Available units"),
        "last_updated": _parse_date(last_updated, "Last updated"),
    }
    result = database["blood_inventory"].update_one(
        {"inventory_id": inventory_id}, {"$set": update}
    )
    if result.matched_count == 0:
        raise ValidationError("Inventory record was not found.")


def delete_inventory(database: Database, inventory_id: str, *, confirmed: bool) -> None:
    if not confirmed:
        raise ValidationError("Confirm deletion before removing an inventory record.")
    result = database["blood_inventory"].delete_one({"inventory_id": inventory_id})
    if result.deleted_count == 0:
        raise ValidationError("Inventory record was not found.")


def create_hospital_request(database: Database, values: dict[str, Any]) -> str:
    document = _make_request_document(database, values)
    try:
        database["hospital_requests"].insert_one(document)
    except DuplicateKeyError:
        raise ValidationError("That request ID already exists.") from None
    return document["request_id"]


def update_hospital_request(
    database: Database,
    request_id: str,
    *,
    requested_units: Any,
    supplied_units: Any,
    priority: str,
) -> None:
    requested = _validate_units(requested_units, "Requested units", minimum=1)
    supplied = _validate_units(supplied_units, "Supplied units")
    if supplied > requested:
        raise ValidationError("Supplied units cannot exceed requested units.")
    if priority not in {"normal", "urgent"}:
        raise ValidationError("Priority must be normal or urgent.")
    pending = requested - supplied
    update = {
        "requested_units": requested,
        "supplied_units": supplied,
        "pending_units": pending,
        "fulfillment_percentage": round(supplied / requested * 100, 2),
        "priority": priority,
        "status": "fulfilled" if pending == 0 else ("partial" if supplied > 0 else "pending"),
    }
    result = database["hospital_requests"].update_one(
        {"request_id": request_id}, {"$set": update}
    )
    if result.matched_count == 0:
        raise ValidationError("Hospital request was not found.")


def delete_hospital_request(
    database: Database,
    request_id: str,
    *,
    confirmed: bool,
) -> None:
    if not confirmed:
        raise ValidationError("Confirm deletion before removing a hospital request.")
    result = database["hospital_requests"].delete_one({"request_id": request_id})
    if result.deleted_count == 0:
        raise ValidationError("Hospital request was not found.")


def install_document_validators(database: Database) -> None:
    validators = {
        "blood_inventory": {
            "bsonType": "object",
            "required": [
                "inventory_id", "bank_id", "bank_name", "location",
                "blood_group", "available_units", "last_updated",
            ],
            "properties": {
                "inventory_id": {"bsonType": "string"},
                "bank_id": {"bsonType": "string"},
                "bank_name": {"bsonType": "string"},
                "location": {"bsonType": "string"},
                "blood_group": {"enum": BLOOD_GROUPS},
                "available_units": {"bsonType": ["int", "long"], "minimum": 0},
                "last_updated": {"bsonType": "date"},
            },
        },
        "hospital_requests": {
            "bsonType": "object",
            "required": [
                "request_id", "hospital_id", "hospital_name", "location",
                "blood_group", "bank_id", "bank_name", "requested_units",
                "supplied_units", "pending_units", "fulfillment_percentage",
                "request_date", "priority", "status",
            ],
            "properties": {
                "request_id": {"bsonType": "string"},
                "hospital_id": {"bsonType": "string"},
                "hospital_name": {"bsonType": "string"},
                "location": {"bsonType": "string"},
                "blood_group": {"enum": BLOOD_GROUPS},
                "bank_id": {"bsonType": "string"},
                "bank_name": {"bsonType": "string"},
                "requested_units": {"bsonType": ["int", "long"], "minimum": 1},
                "supplied_units": {"bsonType": ["int", "long"], "minimum": 0},
                "pending_units": {"bsonType": ["int", "long"], "minimum": 0},
                "fulfillment_percentage": {"bsonType": ["int", "long", "double"]},
                "request_date": {"bsonType": "date"},
                "priority": {"enum": ["normal", "urgent"]},
                "status": {"enum": ["fulfilled", "partial", "pending"]},
            },
        },
    }
    existing = set(database.list_collection_names())
    for collection_name, schema in validators.items():
        if collection_name not in existing:
            database.create_collection(
                collection_name,
                validator={"$jsonSchema": schema},
                validationLevel="strict",
                validationAction="error",
            )
        else:
            database.command(
                "collMod",
                collection_name,
                validator={"$jsonSchema": schema},
                validationLevel="strict",
                validationAction="error",
            )


def ensure_indexes(database: Database) -> None:
    index_fields = {
        "blood_banks": ("bank_id",),
        "hospitals": ("hospital_id",),
        "blood_inventory": ("inventory_id", "blood_group", "location", "bank_id"),
        "donations": ("donation_id", "blood_group", "location", "bank_id", "donation_date"),
        "hospital_requests": (
            "request_id", "blood_group", "location", "bank_id", "hospital_id", "request_date",
        ),
    }
    unique_fields = {
        "blood_banks": "bank_id",
        "hospitals": "hospital_id",
        "blood_inventory": "inventory_id",
        "donations": "donation_id",
        "hospital_requests": "request_id",
    }
    for collection_name, fields in index_fields.items():
        collection: Collection = database[collection_name]
        for field in fields:
            collection.create_index(
                [(field, ASCENDING)],
                unique=field == unique_fields[collection_name],
            )


def _aggregation_match(filters: dict[str, Any], date_field: str) -> dict[str, Any]:
    query: dict[str, Any] = {}
    for field, key in (
        ("blood_group", "blood_group"),
        ("bank_name", "blood_bank"),
        ("location", "location"),
        ("hospital_name", "hospital"),
    ):
        value = filters.get(key)
        if value and value != "All" and (field != "hospital_name" or date_field == "request_date"):
            query[field] = value

    start = filters.get("start_date")
    end = filters.get("end_date")
    if start or end:
        date_range: dict[str, datetime] = {}
        if start:
            date_range["$gte"] = _parse_date(start, "Start date")
        if end:
            date_range["$lt"] = _parse_date(end, "End date") + timedelta(days=1)
        query[date_field] = date_range
    return query


def inventory_totals_pipeline(
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    pipeline: list[dict[str, Any]] = []
    match = _aggregation_match(filters or {}, "last_updated")
    if match:
        pipeline.append({"$match": match})
    pipeline.extend([
        {
            "$group": {
                "_id": {"bank_id": "$bank_id", "blood_group": "$blood_group"},
                "bank_name": {"$first": "$bank_name"},
                "location": {"$first": "$location"},
                "available_units": {"$sum": "$available_units"},
            }
        },
        {"$sort": {"_id.blood_group": 1, "_id.bank_id": 1}},
    ])
    return pipeline


def donation_trends_pipeline(
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    pipeline: list[dict[str, Any]] = []
    match = _aggregation_match(filters or {}, "donation_date")
    if match:
        pipeline.append({"$match": match})
    pipeline.extend([
        {"$match": {"status": "successful"}},
        {
            "$group": {
                "_id": {
                    "$dateTrunc": {"date": "$donation_date", "unit": "month"}
                },
                "donation_units": {"$sum": "$donation_units"},
                "donation_records": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ])
    return pipeline


def hospital_demand_pipeline(
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    pipeline: list[dict[str, Any]] = []
    match = _aggregation_match(filters or {}, "request_date")
    if match:
        pipeline.append({"$match": match})
    pipeline.extend([
        {
            "$group": {
                "_id": {
                    "hospital_id": "$hospital_id",
                    "hospital_name": "$hospital_name",
                    "location": "$location",
                },
                "requested_units": {"$sum": "$requested_units"},
                "supplied_units": {"$sum": "$supplied_units"},
                "pending_units": {"$sum": "$pending_units"},
            }
        },
        {
            "$addFields": {
                "fulfillment_percentage": {
                    "$cond": [
                        {"$gt": ["$requested_units", 0]},
                        {
                            "$multiply": [
                                {"$divide": ["$supplied_units", "$requested_units"]},
                                100,
                            ]
                        },
                        0,
                    ]
                }
            }
        },
        {"$sort": {"requested_units": -1}},
    ])
    return pipeline


def run_aggregation_examples(
    database: Database,
    filters: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    return {
        "inventory_totals": list(
            database["blood_inventory"].aggregate(inventory_totals_pipeline(filters))
        ),
        "donation_trends": list(
            database["donations"].aggregate(donation_trends_pipeline(filters))
        ),
        "hospital_demand": list(
            database["hospital_requests"].aggregate(hospital_demand_pipeline(filters))
        ),
    }
