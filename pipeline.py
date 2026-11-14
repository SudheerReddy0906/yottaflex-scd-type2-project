"""Orchestrates ingestion, validation, idempotency and SCD2 publishing."""
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .database import connect
from .ingestion import read_csv
from .validation import validate_event
from .transformation import rebuild_customer_timeline
from .monitoring import write_report

logger = logging.getLogger(__name__)

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def run_pipeline(input_path, db_path, quarantine_path, report_path):
    run_id = str(uuid.uuid4())
    started = utc_now()
    start_clock = time.perf_counter()
    counts = {"input_count": 0, "accepted_count": 0,
              "duplicate_count": 0, "rejected_count": 0, "output_count": 0}
    errors = []
    conn = connect(db_path)
    conn.execute(
        """INSERT INTO pipeline_runs(run_id, started_at, status)
           VALUES (?, ?, 'RUNNING')""", (run_id, started)
    )
    conn.commit()

    try:
        raw_rows = read_csv(input_path)
        counts["input_count"] = len(raw_rows)
        valid_events = []
        rejects = []
        for raw in raw_rows:
            try:
                valid_events.append((raw, validate_event(raw)))
            except Exception as exc:
                rejects.append((raw, str(exc)))

        # Batch-level ambiguity check: same customer + effective timestamp
        # cannot have two distinct events in the same input batch.
        seen_time = {}
        filtered = []
        for raw, event in valid_events:
            key = (event["customer_id"], event["effective_at"])
            if key in seen_time and seen_time[key] != event["event_id"]:
                rejects.append((raw, "ambiguous: multiple events for customer at same effective_at"))
            else:
                seen_time[key] = event["event_id"]
                filtered.append((raw, event))

        affected_customers = set()
        with conn:
            for raw, reason in rejects:
                conn.execute(
                    """INSERT INTO quarantine(run_id,event_id,customer_id,raw_record,reason)
                       VALUES (?,?,?,?,?)""",
                    (run_id, raw.get("event_id"), raw.get("customer_id"),
                     json.dumps(raw, sort_keys=True), reason)
                )
                counts["rejected_count"] += 1

            for raw, event in filtered:
                existing = conn.execute(
                    "SELECT * FROM event_ledger WHERE event_id=?",
                    (event["event_id"],)
                ).fetchone()
                if existing:
                    same = all(existing[k] == event[k] for k in
                               ("customer_id","customer_name","city","email","effective_at"))
                    if same:
                        counts["duplicate_count"] += 1
                        continue
                    conn.execute(
                        """INSERT INTO quarantine(run_id,event_id,customer_id,raw_record,reason)
                           VALUES (?,?,?,?,?)""",
                        (run_id, event["event_id"], event["customer_id"],
                         json.dumps(raw, sort_keys=True),
                         "event_id already exists with different payload")
                    )
                    counts["rejected_count"] += 1
                    continue

                # Reject a second event at the same effective timestamp,
                # including one already committed in an earlier run.
                conflict = conn.execute(
                    """SELECT event_id FROM event_ledger
                       WHERE customer_id=? AND effective_at=?""",
                    (event["customer_id"], event["effective_at"])
                ).fetchone()
                if conflict:
                    conn.execute(
                        """INSERT INTO quarantine(run_id,event_id,customer_id,raw_record,reason)
                           VALUES (?,?,?,?,?)""",
                        (run_id, event["event_id"], event["customer_id"],
                         json.dumps(raw, sort_keys=True),
                         "ambiguous: customer already has an event at this effective_at")
                    )
                    counts["rejected_count"] += 1
                    continue

                conn.execute(
                    """INSERT INTO event_ledger
                       (event_id,customer_id,customer_name,city,email,effective_at)
                       VALUES (?,?,?,?,?,?)""",
                    tuple(event[k] for k in
                          ("event_id","customer_id","customer_name","city","email","effective_at"))
                )
                counts["accepted_count"] += 1
                affected_customers.add(event["customer_id"])

            for customer_id in sorted(affected_customers):
                rebuild_customer_timeline(conn, customer_id)

            counts["output_count"] = conn.execute(
                "SELECT COUNT(*) FROM customer_dimension"
            ).fetchone()[0]

            ended = utc_now()
            conn.execute(
                """UPDATE pipeline_runs SET ended_at=?, status=?, input_count=?,
                   accepted_count=?, duplicate_count=?, rejected_count=?, output_count=?
                   WHERE run_id=?""",
                (ended, "SUCCESS_WITH_REJECTS" if counts["rejected_count"] else "SUCCESS",
                 counts["input_count"], counts["accepted_count"], counts["duplicate_count"],
                 counts["rejected_count"], counts["output_count"], run_id)
            )

    except Exception as exc:
        errors.append(str(exc))
        ended = utc_now()
        conn.execute(
            """UPDATE pipeline_runs SET ended_at=?, status='FAILED', error_message=?
               WHERE run_id=?""", (ended, str(exc), run_id)
        )
        conn.commit()
        logger.exception("Pipeline run %s failed", run_id)
        raise
    finally:
        conn.close()

    elapsed = round(time.perf_counter() - start_clock, 6)
    report = {
        "run_id": run_id, "started_at": started, "ended_at": ended,
        "status": "SUCCESS_WITH_REJECTS" if counts["rejected_count"] else "SUCCESS",
        **counts, "duration_seconds": elapsed, "errors": errors
    }
    write_report(report, report_path)
    logger.info("Run %s completed: %s", run_id, report)
    return report
