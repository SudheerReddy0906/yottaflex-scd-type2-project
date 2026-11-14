"""Command-line entry point."""
import argparse
import logging
from src.config import DEFAULT_INPUT, DEFAULT_DB, DEFAULT_QUARANTINE, DEFAULT_REPORT
from src.monitoring import configure_logging
from src.pipeline import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="Customer SCD Type 2 pipeline")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--quarantine", default=str(DEFAULT_QUARANTINE))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()
    configure_logging()
    report = run_pipeline(args.input, args.db, args.quarantine, args.report)
    print(report)

if __name__ == "__main__":
    main()
