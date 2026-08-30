"""
Entry point: run a batch (dev-slice or daily-100) through the full
resolve -> crawl -> extract -> match -> validate -> store pipeline.

Usage:
    python -m src.cli.crawl_batch --sample 100
    python -m src.cli.crawl_batch --dev-slice
"""


def main() -> None:
    raise NotImplementedError("Scaffold only — implement pipeline wiring here.")


if __name__ == "__main__":
    main()
