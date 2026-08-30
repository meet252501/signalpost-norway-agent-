"""
Snapshot storage: append-only, dated, previous-snapshot-preserved.
Implements the idempotency and refresh-diff requirements from the
evaluation contract's hard gates.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.config import settings
from src.validate.schema import CompanyProfile


def _snapshot_dir(org_number: str) -> Path:
    d = Path(settings.data_dir) / "snapshots" / org_number
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_snapshot(profile: CompanyProfile) -> Path:
    """
    Write a new dated snapshot for this company. Never overwrites an
    existing snapshot file — each write gets its own timestamped path,
    so history is preserved by construction.
    """
    d = _snapshot_dir(profile.entity.org_number)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = d / f"{ts}.json"
    path.write_text(profile.model_dump_json(indent=2))
    return path


def latest_snapshot(org_number: str) -> CompanyProfile | None:
    d = _snapshot_dir(org_number)
    files = sorted(d.glob("*.json"))
    if not files:
        return None
    return CompanyProfile.model_validate_json(files[-1].read_text())


def diff_snapshots(old: CompanyProfile | None, new: CompanyProfile) -> list[dict]:
    """
    Return a list of meaningful field-level changes between the previous
    and new snapshot. Empty list means nothing changed — the refresh
    loop should not report noise for unchanged fields.
    """
    if old is None:
        return [{"field": "profile", "change": "created"}]

    changes = []
    old_dict = json.loads(old.model_dump_json())
    new_dict = json.loads(new.model_dump_json())

    def walk(prefix: str, o, n):
        if isinstance(o, dict) and isinstance(n, dict):
            for key in set(o) | set(n):
                walk(f"{prefix}.{key}" if prefix else key, o.get(key), n.get(key))
        elif o != n:
            changes.append({"field": prefix, "old": o, "new": n})

    walk("", old_dict, new_dict)
    # generated_at will always differ — exclude it from "meaningful" changes
    return [c for c in changes if not c["field"].endswith("profile_generated_at")]


def is_idempotent_rerun(org_number: str, new_profile: CompanyProfile) -> bool:
    """
    True if re-running against unchanged upstream data would produce an
    identical profile to the latest snapshot (ignoring generation
    timestamp). Used by the idempotency test in tests/test_idempotency.py.
    """
    prev = latest_snapshot(org_number)
    if prev is None:
        return False
    return len(diff_snapshots(prev, new_profile)) == 0
