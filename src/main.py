"""
Main batch entrypoint for the Signalpost challenge.
Processes an input JSONL of org numbers and outputs the result envelopes.
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import TextIO

from src.budget import BatchBudget, BudgetExceeded
from src.pipeline import process_company

# Adjust log level for cleaner output
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_batch(input_file: TextIO, output_file: TextIO) -> None:
    budget = BatchBudget()
    logger.info(
        f"Starting batch with budget: {budget.max_requests} reqs, "
        f"{budget.max_wallclock} secs."
    )

    for line in input_file:
        line = line.strip()
        if not line:
            continue

        try:
            data = json.loads(line)
            org_number = data.get("org_number") or data.get("organisation_number")
        except json.JSONDecodeError:
            # If it's just a string, assume it's the org number
            org_number = line

        if not org_number:
            continue

        try:
            # Abort before fetching if budget looks dry
            if not budget.can_spend_request():
                logger.error("Budget exhausted before company. Ending batch.")
                break

            from src.storage.snapshot import diff_snapshots, latest_snapshot, write_snapshot
            from src.validate.schema import RefreshMetadata

            result = process_company(org_number, budget)
            
            if result.status == "completed" and result.profile:
                prev = latest_snapshot(org_number)
                diffs = diff_snapshots(prev, result.profile)
                write_snapshot(result.profile)
                
                result.refresh = RefreshMetadata(
                    previous_snapshot_at=prev.profile_generated_at if prev else None,
                    material_changes=diffs,
                    change_count=len(diffs)
                )

            output_file.write(result.model_dump_json() + "\n")
            output_file.flush()

        except BudgetExceeded as e:
            logger.error(f"Budget exceeded during processing: {e}")
            break
        except Exception as e:
            logger.exception(f"Unhandled error on {org_number}: {e}")

    logger.info("Batch completed.")
    logger.info(f"Final Budget Summary: {budget.summary()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Signalpost Agent Batch Runner")
    parser.add_argument(
        "-i",
        "--input",
        type=argparse.FileType("r", encoding="utf-8"),
        required=True,
        help="Input JSONL file of companies (universe.jsonl)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w", encoding="utf-8"),
        required=True,
        help="Output JSONL file to write results to",
    )
    args = parser.parse_args()

    run_batch(args.input, args.output)
