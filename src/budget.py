"""
Per-batch budget tracker.

Every outbound HTTP call MUST increment the counter BEFORE the request
fires (check-then-act). The 2,000-request cap is a hard gate — exceeding
it during evaluation = disqualification.

Usage:
    budget = BatchBudget()
    budget.check_and_spend()  # raises BudgetExceeded if exhausted
    # ... make the request ...
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from src.config import settings

logger = logging.getLogger(__name__)


class BudgetExceeded(RuntimeError):
    """Raised when the per-batch budget is exhausted."""


@dataclass
class BatchBudget:
    """Thread-safe budget counter for a single 100-company batch."""

    max_requests: int = field(default_factory=lambda: settings.max_requests_per_batch)
    max_wallclock: int = field(default_factory=lambda: settings.max_wallclock_seconds)
    max_cost_usd: float = field(default_factory=lambda: float(settings.max_declared_cost_usd))

    requests_used: int = 0
    declared_cost_usd: float = 0.0
    _start_time: float = field(default_factory=time.monotonic)

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._start_time

    def remaining_requests(self) -> int:
        return max(0, self.max_requests - self.requests_used)

    def can_spend_request(self) -> bool:
        if self.requests_used >= self.max_requests:
            return False
        if self.elapsed_seconds() >= self.max_wallclock:
            return False
        return True

    def check_and_spend(self, url: str = "") -> None:
        """Check-then-spend — call BEFORE every outbound request."""
        if self.requests_used >= self.max_requests:
            raise BudgetExceeded(
                f"Request budget exhausted ({self.requests_used}/{self.max_requests}) "
                f"before fetching {url}"
            )
        elapsed = self.elapsed_seconds()
        if elapsed >= self.max_wallclock:
            raise BudgetExceeded(
                f"Wall-clock budget exhausted ({elapsed:.0f}s/{self.max_wallclock}s) "
                f"before fetching {url}"
            )
        self.requests_used += 1
        if self.requests_used % 100 == 0:
            logger.info(
                "Budget: %d/%d requests, %.0fs elapsed, $%.2f spent",
                self.requests_used,
                self.max_requests,
                elapsed,
                self.declared_cost_usd,
            )

    def add_cost(self, amount_usd: float) -> None:
        self.declared_cost_usd += amount_usd
        if self.declared_cost_usd > self.max_cost_usd:
            raise BudgetExceeded(
                f"Declared cost exceeded (${self.declared_cost_usd:.2f}/${self.max_cost_usd:.2f})"
            )

    def summary(self) -> dict:
        return {
            "requests_used": self.requests_used,
            "requests_max": self.max_requests,
            "wallclock_seconds": round(self.elapsed_seconds(), 1),
            "wallclock_max": self.max_wallclock,
            "declared_cost_usd": round(self.declared_cost_usd, 2),
            "cost_max_usd": self.max_cost_usd,
        }
