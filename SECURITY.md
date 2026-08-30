# Security & Secrets Handling

- Never commit `.env`, API keys, or credentials. `.env.example` documents
  required variables with empty values only.
- All discovered URLs must pass through the sanitizer in `src/crawl/`
  before fetching — no requests to internal/private IP ranges, no
  following redirects to disallowed domains (SSRF protection).
- No crawling behind authentication/login walls.
- Server-side secrets (any paid API keys) are read from environment
  variables only, never hardcoded, never logged.
- Per the evaluation contract's hard gate: "documented source rights,
  server-side secrets, safe URL handling" — treat this as a submission
  blocker, not a nice-to-have.

If this repo is ever made public: rotate any keys that touched `.env`
locally before doing so, and double-check `.gitignore` coverage first.
