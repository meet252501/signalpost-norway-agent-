# Dashboard (Phase 8 scaffold)

Placeholder for the profile browser: search, compare, "what changed
since last snapshot," and visibility into *why* a field is missing
(blocked vs not found vs not applicable).

Not built yet — this is intentionally last priority per
`docs/scoring_and_gates.md` (UX is 5% of the score; correctness work
in `src/resolve`, `src/crawl`, `src/match`, `src/validate` comes first).

Once started:
```
cd frontend
npm install
npm run dev
```
Point it at the FastAPI app in `src/api/main.py` (`make` doesn't run
this yet — add an `api` target when the app has real routes).
