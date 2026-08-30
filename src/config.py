"""
Central config loader. Reads budget guardrails and API keys from the
environment (see .env.example). Import `settings` anywhere it's needed
instead of calling os.environ directly, so every module shares one
source of truth and one place to change defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    val = os.environ.get(name)
    return int(val) if val else default


@dataclass(frozen=True)
class Settings:
    search_api_key: str | None = os.environ.get("SEARCH_API_KEY") or None
    company_data_api_key: str | None = os.environ.get("COMPANY_DATA_API_KEY") or None

    max_requests_per_batch: int = _int_env("MAX_REQUESTS_PER_BATCH", 2000)
    # 43 min with 2 min safety margin
    max_wallclock_seconds: int = _int_env("MAX_WALLCLOCK_SECONDS", 2580)
    max_declared_cost_usd: int = _int_env("MAX_DECLARED_COST_USD", 10)

    dev_slice_size: int = _int_env("DEV_SLICE_SIZE", 250)

    data_dir: str = os.environ.get("DATA_DIR", "data")


settings = Settings()
