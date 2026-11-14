import sqlite3
from src.pipeline import run_pipeline

def event(event_id, city, date):
    return {"event_id":event_id,"customer_id":"C1","customer_name":"Asha",
            "city":city,"email":"asha@example.com","effective_at":date}

def execute(tmp_path, write_events, rows, name="input.csv"):
    inp = write_events(name, rows)
    db = tmp_path / "test.db"
    q = tmp_path / "quarantine.jsonl"
    report = tmp_path / "report.json"
    result = run_pipeline(inp, db, q, report)
    return result, db

def test_happy_path_creates_history(tmp_path, write_events):
    result, db = execute(tmp_path, write_events, [
        event("E1","Anantapur","2025-01-01T00:00:00Z"),
        event("E2","Bengaluru","2025-02-01T00:00:00Z")
    ])
    assert result["accepted_count"] == 2
    con = sqlite3.connect(db)
    rows = con.execute("SELECT city,effective_to,is_current FROM customer_dimension ORDER BY effective_from").fetchall()
    con.close()
    assert rows == [("Anantapur","2025-02-01T00:00:00+00:00",0),
                    ("Bengaluru",None,1)]

def test_rerun_is_idempotent(tmp_path, write_events):
    rows = [event("E1","Anantapur","2025-01-01T00:00:00Z")]
    first, db = execute(tmp_path, write_events, rows)
    second, _ = execute(tmp_path, write_events, rows, "same.csv")
    assert first["accepted_count"] == 1
    assert second["duplicate_count"] == 1
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM customer_dimension").fetchone()[0] == 1
    con.close()

def test_late_arriving_change_rebuilds_timeline(tmp_path, write_events):
    _, db = execute(tmp_path, write_events, [
        event("E1","Anantapur","2025-01-01T00:00:00Z"),
        event("E3","Chennai","2025-03-01T00:00:00Z")
    ])
    # An event effective in February arrives in a later batch.
    execute(tmp_path, write_events, [
        event("E2","Bengaluru","2025-02-01T00:00:00Z")
    ], "late.csv")
    con = sqlite3.connect(db)
    rows = con.execute("SELECT city,effective_from,effective_to,is_current FROM customer_dimension ORDER BY effective_from").fetchall()
    con.close()
    assert [r[0] for r in rows] == ["Anantapur","Bengaluru","Chennai"]
    assert rows[0][2] == "2025-02-01T00:00:00+00:00"
    assert rows[1][2] == "2025-03-01T00:00:00+00:00"
    assert rows[2][3] == 1

def test_repeated_snapshot_does_not_create_version(tmp_path, write_events):
    result, db = execute(tmp_path, write_events, [
        event("E1","Anantapur","2025-01-01T00:00:00Z"),
        event("E2","Anantapur","2025-02-01T00:00:00Z")
    ])
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM customer_dimension").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM event_ledger").fetchone()[0] == 2
    con.close()

def test_invalid_null_is_quarantined(tmp_path, write_events):
    bad = event("E1","", "2025-01-01T00:00:00Z")
    result, db = execute(tmp_path, write_events, [bad])
    assert result["rejected_count"] == 1
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0] == 1
    con.close()

def test_empty_input_is_safe(tmp_path, write_events):
    result, db = execute(tmp_path, write_events, [])
    assert result["input_count"] == 0
    assert result["output_count"] == 0

def test_malformed_timestamp_is_quarantined(tmp_path, write_events):
    bad = event("E1","Anantapur","not-a-date")
    result, _ = execute(tmp_path, write_events, [bad])
    assert result["rejected_count"] == 1

def test_same_timestamp_conflict_is_rejected(tmp_path, write_events):
    rows = [event("E1","Anantapur","2025-01-01T00:00:00Z"),
            event("E2","Bengaluru","2025-01-01T00:00:00Z")]
    result, _ = execute(tmp_path, write_events, rows)
    assert result["rejected_count"] == 1
