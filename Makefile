.PHONY: install dev-install lint format test check crawl-dev score freeze

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements-dev.txt
	playwright install --with-deps chromium

lint:
	ruff check .

format:
	ruff format .

test:
	pytest -v

check: lint test

crawl-dev:
	python -m src.cli.crawl_batch --dev-slice

score:
	python -m src.cli.score_batch

freeze:
	@echo "Run pre-freeze checklist in docs/scoring_and_gates.md before tagging."
	git tag -a "freeze-$$(date +%Y%m%d-%H%M)" -m "Frozen for daily/random evaluation"
