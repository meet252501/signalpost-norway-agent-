# Contributing / Working Notes

Solo project for the Builderr.ai Signalpost challenge, but keeping this file
in case of collaborators (or future-me after a break).

## Workflow
1. Branch off `main` for any non-trivial change: `feature/<short-name>`
2. Run `make check` before committing (lint + tests)
3. Merge to `main` only when the dev-slice metrics haven't regressed
   (see `docs/learning_harness.md`)
4. Tag a commit hash as frozen right before each daily cutoff / revision
   submission — see `docs/scoring_and_gates.md` pre-freeze checklist

## Code style
- Python: `ruff` for lint + format (config in `pyproject.toml`)
- Type hints required on all public functions
- Docstrings on every module and public class

## Commit messages
Short imperative subject line, optional body. Reference the plan phase
when relevant, e.g. `[Phase 2] add sitemap-first crawl spider`.

## Never commit
- `.env` or any real API keys
- Anything under `data/raw`, `data/processed`, `data/snapshots`
  (all gitignored — regenerate, don't commit)
