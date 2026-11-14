"""SCD Type 2 timeline reconstruction."""
from .config import TRACKED_COLUMNS

def rebuild_customer_timeline(conn, customer_id: str) -> int:
    """
    Rebuild one customer's dimension timeline from the accepted event ledger.

    effective_to is exclusive: a version is valid for
    [effective_from, effective_to). The final version has effective_to NULL.
    Multiple events for one customer at the exact same effective timestamp
    are rejected during ingestion because their ordering is ambiguous.
    """
    events = conn.execute(
        """SELECT event_id, customer_id, customer_name, city, email, effective_at
           FROM event_ledger WHERE customer_id=?
           ORDER BY effective_at, event_id""", (customer_id,)
    ).fetchall()

    # Keep only actual state changes. Repeated snapshots are retained in the
    # event ledger but do not create redundant dimension versions.
    changes = []
    previous_state = None
    for event in events:
        state = tuple(event[col] for col in TRACKED_COLUMNS)
        if state != previous_state:
            changes.append((event, state))
            previous_state = state

    conn.execute("DELETE FROM customer_dimension WHERE customer_id=?", (customer_id,))
    for index, (event, state) in enumerate(changes):
        next_effective = (
            changes[index + 1][0]["effective_at"]
            if index + 1 < len(changes) else None
        )
        conn.execute(
            """INSERT INTO customer_dimension
               (customer_id, customer_name, city, email,
                effective_from, effective_to, is_current, source_event_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (customer_id, *state, event["effective_at"], next_effective,
             1 if next_effective is None else 0, event["event_id"])
        )
    return len(changes)
