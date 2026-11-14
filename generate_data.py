"""Generate deterministic synthetic customer event CSV data."""
import argparse
import csv
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

CITIES = ["Anantapur", "Bengaluru", "Hyderabad", "Chennai", "Pune"]

def generate(path, customers=1000, events_per_customer=3, seed=42):
    random.seed(seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for c in range(1, customers + 1):
        customer_id = f"C{c:06d}"
        name = f"Customer {c}"
        city = random.choice(CITIES)
        email = f"customer{c}@example.com"
        for e in range(events_per_customer):
            effective = base + timedelta(days=e * 30 + random.randint(0, 3))
            # A deterministic state change after the initial version.
            if e > 0:
                city = random.choice([x for x in CITIES if x != city])
            rows.append({
                "event_id": f"EV-{c:06d}-{e+1:03d}",
                "customer_id": customer_id,
                "customer_name": name,
                "city": city,
                "email": email,
                "effective_at": effective.isoformat().replace("+00:00", "Z")
            })
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "event_id","customer_id","customer_name","city","email","effective_at"
        ])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {len(rows)} events at {path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/input/large_customer_events.csv")
    parser.add_argument("--customers", type=int, default=1000)
    parser.add_argument("--events-per-customer", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate(args.output, args.customers, args.events_per_customer, args.seed)
