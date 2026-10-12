from __future__ import annotations

from src.data_generation import clean_and_save_datasets
from src.db.connection import DatabaseConnection
from src.db.repository import ensure_document_validators, ensure_indexes

COLLECTIONS = {
    "blood_banks": "bank_id",
    "hospitals": "hospital_id",
    "blood_inventory": "inventory_id",
    "donations": "donation_id",
    "hospital_requests": "request_id",
}


def seed_database() -> dict[str, int | str]:
    try:
        connection = DatabaseConnection()
        database = connection.connect()
    except ConnectionError as exc:
        print(f"MongoDB connection unavailable: {exc}")
        return {"status": "skipped", "inserted": 0}

    if database is None:
        return {"status": "skipped", "inserted": 0}

    try:
        result = clean_and_save_datasets()
        ensure_indexes(database)
        inserted = 0
        for collection_name, id_field in COLLECTIONS.items():
            collection = database[collection_name]
            records = result["cleaned"][collection_name].to_dict("records")
            for record in records:
                record["_id"] = record[id_field]
                write_result = collection.update_one(
                    {"_id": record["_id"]},
                    {"$setOnInsert": record},
                    upsert=True,
                )
                inserted += int(write_result.upserted_id is not None)

        ensure_document_validators(database)
        return {
            "status": "success",
            "inserted": inserted,
            "rejected": len(result["issues"]),
        }
    finally:
        connection.close()


if __name__ == "__main__":
    result = seed_database()
    print(result)
