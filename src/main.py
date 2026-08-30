"""
Main batch entrypoint for the Signalpost challenge.
Processes an input JSONL of org numbers and outputs the result envelopes.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import TextIO

from src.budget import BatchBudget, BudgetExceeded
from src.pipeline import process_company

# Adjust log level for cleaner output
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_batch(input_file: TextIO, output_file: TextIO) -> None:
    budget = BatchBudget()
    logger.info(
        f"Starting batch with budget: {budget.max_requests} requests, {budget.max_wallclock} seconds."
    )

    for line in input_file:
        line = line.strip()
        if not line:
            continue

        try:
            data = json.loads(line)
            org_number = data.get("org_number")
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

            result = process_company(org_number, budget)
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
        "--input", "-i", type=argparse.FileType("r"), default=sys.stdin, help="Input JSONL file"
    )
    parser.add_argument(
        "--output", "-o", type=argparse.FileType("w"), default=sys.stdout, help="Output JSONL file"
    )
    args = parser.parse_args()

    run_batch(args.input, args.output)
