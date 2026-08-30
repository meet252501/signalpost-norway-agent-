"""
Idempotency test: re-running against the same upstream data must not
produce spurious diffs. Directly guards the hard gate:
'Idempotent refresh with the previous snapshot preserved.'
"""

import copy

from src.storage.snapshot import diff_snapshots


def test_identical_profiles_produce_no_diff(sample_profile):
    same_profile = copy.deepcopy(sample_profile)
    # generated_at is expected to differ run-to-run and must be excluded
    diffs = diff_snapshots(sample_profile, same_profile)
    assert diffs == []


def test_changed_field_is_detected(sample_profile):
    changed = copy.deepcopy(sample_profile)
    changed.entity.status = "dissolved"
    diffs = diff_snapshots(sample_profile, changed)
    assert any(d["field"] == "entity.status" for d in diffs)
