"""SQLite schema and persistence operations."""
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS event_ledger (
    event_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    city TEXT NOT NULL,
    email TEXT NOT NULL,
    effective_at TEXT NOT NULL,
    received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_event_customer_time
    ON event_ledger(customer_id, effective_at, event_id);

CREATE TABLE IF NOT EXISTS customer_dimension (
    customer_sk INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    city TEXT NOT NULL,
    email TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    is_current INTEGER NOT NULL CHECK (is_current IN (0,1)),
    source_event_id TEXT NOT NULL,
    UNIQUE(customer_id, effective_from)
);
CREATE INDEX IF NOT EXISTS idx_dim_customer_current
    ON customer_dimension(customer_id, is_current);

CREATE TABLE IF NOT EXISTS quarantine (
    quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    event_id TEXT,
    customer_id TEXT,
    raw_record TEXT NOT NULL,
    reason TEXT NOT NULL,
    rejected_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL,
    input_count INTEGER NOT NULL DEFAULT 0,
    accepted_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    output_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);
"""

def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn
