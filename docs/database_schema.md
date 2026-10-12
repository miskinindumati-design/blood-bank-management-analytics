# Database Schema and Example Documents

## Database name

`blood_bank_analytics`

## Collections

### 1. blood_banks

Purpose: Stores blood-bank metadata, location, and operational capacity.

| Field | Type | Description |
| --- | --- | --- |
| `_id` | ObjectId/String | Unique bank identifier |
| `bank_id` | string | Example: `BB-101` |
| `bank_name` | string | Example: `Lifeline Blood Bank` |
| `location` | string | City or area |
| `city` | string | City name |
| `contact` | string | Phone or contact info |

Example document:

```json
{
  "_id": "BB-101",
  "bank_id": "BB-101",
  "bank_name": "Lifeline Blood Bank",
  "location": "Bengaluru",
  "city": "Bengaluru",
  "contact": "+91-80-000-1001"
}
```

### 2. hospitals

Purpose: Stores hospital metadata and service location.

| Field | Type | Description |
| --- | --- | --- |
| `_id` | ObjectId/String | Unique hospital identifier |
| `hospital_id` | string | Example: `H-01` |
| `hospital_name` | string | Hospital name |
| `location` | string | Area name |
| `city` | string | City name |

Example document:

```json
{
  "_id": "H-01",
  "hospital_id": "H-01",
  "hospital_name": "CityCare General Hospital",
  "location": "Bengaluru",
  "city": "Bengaluru"
}
```

### 3. blood_inventory

Purpose: Tracks current stock levels by blood group per blood bank.

| Field | Type | Description |
| --- | --- | --- |
| `_id` | ObjectId/String | Unique inventory record |
| `inventory_id` | string | Example: `INV-BB-101-A+` |
| `bank_id` | string | Blood bank reference |
| `bank_name` | string | Blood bank name |
| `location` | string | Inventory location |
| `blood_group` | string | A+, A-, etc. |
| `available_units` | int | Current stock |
| `last_updated` | BSON Date | Last update timestamp |

Example document:

```json
{
  "_id": "INV-BB-101-A+",
  "inventory_id": "INV-BB-101-A+",
  "bank_id": "BB-101",
  "bank_name": "Lifeline Blood Bank",
  "location": "Bengaluru",
  "blood_group": "A+",
  "available_units": 59,
  "last_updated": {"$date": "2025-06-30T00:00:00Z"}
}
```

### 4. donations

Purpose: Records blood donations received by banks.

| Field | Type | Description |
| --- | --- | --- |
| `_id` | ObjectId/String | Unique donation record |
| `donation_id` | string | Example: `DON-0001` |
| `donor_age` | int | Donor age |
| `blood_group` | string | Donation group |
| `donation_units` | int | Units collected |
| `donation_date` | BSON Date | Date of donation |
| `bank_id` | string | Collection bank |
| `bank_name` | string | Collection bank name |
| `location` | string | Donation location |
| `donor_type` | string | Voluntary or replacement |
| `status` | string | Successful/failed |

Example document:

```json
{
  "_id": "DON-0001",
  "donation_id": "DON-0001",
  "donor_age": 52,
  "blood_group": "O+",
  "donation_units": 2,
  "donation_date": {"$date": "2024-10-25T00:00:00Z"},
  "bank_id": "BB-202",
  "bank_name": "Mercy Blood Centre",
  "location": "Mysuru",
  "donor_type": "voluntary",
  "status": "successful"
}
```

### 5. hospital_requests

Purpose: Stores demand requests from hospitals, including fulfillment and pending units.

| Field | Type | Description |
| --- | --- | --- |
| `_id` | ObjectId/String | Unique request record |
| `request_id` | string | Example: `REQ-0001` |
| `hospital_id` | string | Hospital reference |
| `hospital_name` | string | Hospital name |
| `location` | string | Hospital location |
| `blood_group` | string | Required blood group |
| `bank_id` | string | Requested bank |
| `bank_name` | string | Requested bank name |
| `requested_units` | int | Units requested |
| `supplied_units` | int | Units supplied |
| `pending_units` | int | Remaining demand |
| `fulfillment_percentage` | float | Percent supplied |
| `request_date` | BSON Date | Date of request |
| `priority` | string | urgent/normal |
| `status` | string | fulfilled/partial/pending |

Example document:

```json
{
  "_id": "REQ-0001",
  "request_id": "REQ-0001",
  "hospital_id": "H-02",
  "hospital_name": "Green Valley Hospital",
  "location": "Mysuru",
  "blood_group": "O+",
  "bank_id": "BB-202",
  "bank_name": "Mercy Blood Centre",
  "requested_units": 10,
  "supplied_units": 7,
  "pending_units": 3,
  "fulfillment_percentage": 70.0,
  "request_date": {"$date": "2025-05-04T00:00:00Z"},
  "priority": "urgent",
  "status": "partial"
}
```

## Why MongoDB is appropriate

MongoDB is appropriate because the project contains evolving data with different shapes and nested operational context. It supports fast document-based inserts, flexible queries, and analytical aggregates for blood bank and hospital records without rigid row-based schema constraints.

## Identifiers, indexes, validation, and references

Each collection uses the matching application ID as both `_id` and its named ID field (`bank_id`, `hospital_id`, `inventory_id`, `donation_id`, or `request_id`). MongoDB enforces uniqueness for `_id`; `src/db/seed.py` also creates unique indexes on each named ID and query indexes on blood group, location, bank/hospital IDs, and relevant dates.

The preprocessing pipeline validates required fields, identifier uniqueness, blood groups, dates, units, status consistency, and bank/hospital references before writing CSVs or seeding. The management UI validates create/update payloads and confirms deletion. MongoDB JSON Schema validators are installed for `blood_inventory` and `hospital_requests` by the seeder and before UI write operations. References are checked against bank and hospital documents in application code; MongoDB does not provide relational foreign-key enforcement.

## Aggregation pipeline examples

The application executes MongoDB aggregation pipelines and displays their results in the dashboard:

1. `blood_inventory`: groups by blood bank and blood group and sums available units.
2. `donations`: groups successful synthetic donation records by calendar month and sums donation units and record counts.
3. `hospital_requests`: groups by hospital, sums requested/supplied/pending units, and computes fulfillment percentage from the totals.

The seed operation is idempotent and only inserts missing IDs using `$setOnInsert`; it does not reset or replace existing records.
