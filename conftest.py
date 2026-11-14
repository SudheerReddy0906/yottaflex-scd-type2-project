import csv
import pytest

@pytest.fixture
def write_events(tmp_path):
    def _write(name, rows):
        path = tmp_path / name
        fields = ["event_id","customer_id","customer_name","city","email","effective_at"]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path
    return _write
