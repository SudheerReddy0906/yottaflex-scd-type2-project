# Design Decisions and Trade-offs

## Timeline reconstruction

The event ledger is the source of truth for accepted events. For each affected customer, the pipeline sorts all events by effective timestamp and rebuilds the dimension. This is simple to reason about and correctly supports late-arriving events.

## Idempotency

`event_ledger.event_id` is a primary key. Replaying the same event ID and identical payload is counted as a duplicate and does not change the dimension. Reusing an event ID with a different payload is quarantined.

## Change detection

Only tracked attributes (`customer_name`, `city`, `email`) determine a new version. Repeated consecutive snapshots do not create extra versions.

## Ambiguous same-time events

Events for the same customer at the same effective timestamp are rejected. A production source should provide a sequence number or deterministic source ordering if same-time changes are legitimate.

## Transaction boundary

Accepted ledger inserts, quarantine writes, and affected-customer dimension rebuilds happen in one SQLite transaction. A failed transaction rolls back data changes.

## Scale and optimization

The implementation indexes the event ledger by `(customer_id, effective_at, event_id)` and rebuilds only customers touched by the current batch. For very large histories, replace full per-customer reconstruction with an incremental interval-splitting algorithm and use a warehouse database.

## Limitations

- The source must provide complete snapshots.
- The project is a local SQLite demonstration, not a distributed streaming system.
- `customer_sk` values can change when a customer's dimension history is rebuilt; downstream systems should use a stable business key or a production-grade surrogate-key migration strategy if facts already reference these keys.
- The example does not implement deletion/tombstone events.
