"""Input schema and business-rule validation."""
from datetime import datetime, timezone
from .config import REQUIRED_COLUMNS, TRACKED_COLUMNS

def parse_timestamp(value: str) -> datetime:
    """Parse ISO-8601 timestamp; naive timestamps are interpreted as UTC."""
    if value is None or not str(value).strip():
        raise ValueError("effective_at is required")
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("effective_at must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def validate_event(row: dict) -> dict:
    """Return normalized event or raise ValueError with a clear reason."""
    missing = [c for c in REQUIRED_COLUMNS if c not in row]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")
    event = {k: ("" if row.get(k) is None else str(row.get(k)).strip())
             for k in REQUIRED_COLUMNS}
    for key in ("event_id", "customer_id"):
        if not event[key]:
            raise ValueError(f"{key} must not be blank")
    for key in TRACKED_COLUMNS:
        if not event[key]:
            raise ValueError(f"{key} must not be blank")
    event["effective_at"] = parse_timestamp(event["effective_at"]).isoformat()
    return event
