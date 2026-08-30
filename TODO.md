# TODO

## First step, before anything else
- [ ] Read `AGENTS.md` in full — it's the entry point for any coding
      agent (Antigravity, Claude Code, etc.) building this project
- [ ] Read `docs/RESEARCH.md` — the pre-build research synthesis
      (entity-resolution literature, verified registry API, structured-
      data coverage ceiling) that several architecture decisions below
      depend on
- [ ] `make dev-install && pytest tests/ -v` — confirm everything that
      already has implementation code actually runs in a real
      environment (it was written and reviewed but only pure-Python
      logic was executable in the sandbox that built this scaffold;
      anything needing pydantic/rapidfuzz/requests was never run)
- [ ] Evaluate the `brreg` PyPI client and Splink (see
      `docs/RESEARCH.md` §4) before committing to hand-rolled
      alternatives already stubbed in `src/resolve/` and `src/match/`

## Before writing any code
- [ ] Download full 411,160-company universe + verify published hash
- [ ] Download and read the runnable reference agent end-to-end
- [ ] Download and read: challenge brief, output contract, source policy,
      agent playbook, evaluation contract, 100-company sample
- [ ] Paste real output contract into `docs/data_schema.md`, replacing
      the working sketch
- [ ] Paste real source policy into `docs/source_policy.md`
- [ ] Create GitHub repo, push this scaffold, set up branch protection
      on `main` (freeze discipline starts here)
- [ ] Pin dependency versions in `requirements.txt`

## Phase 0 setup
- [ ] Python venv + install deps
- [ ] `.env` from `.env.example`, fill in any needed API keys
- [ ] Pick and freeze the 200–300 company dev slice
- [ ] Set up CI (lint + tests) even if minimal — catches regressions
      before they hit a frozen submission

## Ongoing
- [ ] Keep `PROJECT_PLAN.md` phase checkboxes current
- [ ] Log every learning-harness trial (see `docs/learning_harness.md`)
- [ ] Track budget per batch run (see `docs/api_and_budget.md`)
- [ ] Pre-freeze checklist before every commit-hash freeze
      (see `docs/scoring_and_gates.md`)

## Before first submission
- [ ] Full-scale run ≥1,000 companies completed
- [ ] Idempotency test passes on full-scale data
- [ ] Manual spot-check of 20+ random profiles for wrong-company errors
- [ ] Submission package assembled: org-number manifest, run command,
      models/APIs used, licences, expected cost per 100-company batch
