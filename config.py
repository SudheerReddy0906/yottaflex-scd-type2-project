"""Central configuration for the SCD Type 2 pipeline."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "input" / "customer_events.csv"
DEFAULT_DB = PROJECT_ROOT / "data" / "output" / "scd2.db"
DEFAULT_QUARANTINE = PROJECT_ROOT / "data" / "quarantine" / "rejected_records.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "latest_run.json"

REQUIRED_COLUMNS = (
    "event_id", "customer_id", "customer_name", "city",
    "email", "effective_at"
)
TRACKED_COLUMNS = ("customer_name", "city", "email")
