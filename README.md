# Customer Data History Management Using SCD Type 2

A runnable Python + SQLite data engineering solution for the YottaFlex.ai SCD Type 2 challenge.

## Features

- SCD Type 2 history with inclusive `effective_from`, exclusive `effective_to`, and `is_current`.
- Change detection across customer name, city, and email.
- Repeated identical snapshots do not create redundant dimension versions.
- Late-arriving events rebuild only the affected customer's timeline.
- Idempotent replay using a unique source `event_id`.
- Schema/business-rule validation and quarantine with rejection reasons.
- Run IDs, timestamps, row counts, status, duration, and JSON run report.
- Automated tests for happy path, rerun, late arrival, repeated updates, nulls, malformed timestamps, empty input, and same-time conflicts.

## Requirements

- Python 3.10+
- pytest (for tests)

The pipeline itself uses only the Python standard library.

## Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Run the sample

From the repository root:

```bash
python main.py
```

Optional paths:

```bash
python main.py --input data/input/customer_events.csv --db data/output/scd2.db --quarantine data/quarantine/rejected_records.jsonl --report reports/latest_run.json
```

The sample includes an out-of-order event for CUST001, a repeated event, and an invalid row. The pipeline should accept valid new events, count the replay as a duplicate, and quarantine invalid input. The final sample row replays event ID EV002 with the same payload, so it is counted as a duplicate.

## Run tests

```bash
pytest -q
```

## Generate a larger reproducible dataset

```bash
python generate_data.py --output data/input/large_customer_events.csv --customers 10000 --events-per-customer 4 --seed 42
python main.py --input data/input/large_customer_events.csv --db data/output/large.db --report reports/large_run.json
```

## Inspect the database

Use any SQLite client or Python. Example:

```sql
SELECT customer_id, customer_name, city, effective_from, effective_to, is_current
FROM customer_dimension
ORDER BY customer_id, effective_from;
```

Run the queries in `sql/reconciliation.sql` to check current-row counts and interval overlaps. The validation queries should return zero rows for a consistent result.

## Pipeline flow

```text
CSV source
   |
   v
Ingestion -> Schema/business validation -> Quarantine invalid rows
   |                                      |
   v                                      v
Idempotency check                    quarantine table
   |
   v
Accepted event ledger
   |
   v
Rebuild affected customer timeline
   |
   v
SCD2 customer dimension -> Reconciliation / run report
```

## Output artifacts

- SQLite database: `data/output/scd2.db`
- Rejected records: `data/quarantine/rejected_records.jsonl` (quarantine table is authoritative)
- Latest run report: `reports/latest_run.json`

## SCD Type 2 example

| customer_id | city | effective_from | effective_to | is_current |
|---|---|---|---|---:|
| CUST001 | Anantapur | 2025-01-01 | 2025-02-01 | 0 |
| CUST001 | Anantapur | 2025-02-01 | 2025-03-01 | 0 |
| CUST001 | Bengaluru | 2025-03-01 | NULL | 1 |

The exact sample history depends on the accepted events. A repeated same-state event does not add a version.

## Important implementation notes

- A timestamp without timezone is interpreted as UTC.
- `effective_to` is exclusive to avoid boundary overlap.
- Different events for the same customer and same effective timestamp are rejected as ambiguous.
- Reprocessing identical event IDs is safe.
- Late-arriving events are supported by rebuilding that customer's timeline from the event ledger.

## Suggested GitHub repository description

`A modular Python and SQLite SCD Type 2 pipeline demonstrating effective dating, change detection, idempotent ingestion, late-arriving event handling, quarantine, operational metrics, and automated tests.`

## Before submission

1. Run `pytest -q` and ensure all tests pass.
2. Run `python main.py` and inspect the database.
3. Run reconciliation SQL and capture evidence.
4. Include a screenshot of test output and sample dimension rows in your repository.
5. Do not commit generated database files or personal data.
