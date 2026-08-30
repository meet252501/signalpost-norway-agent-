from unittest.mock import MagicMock, patch

from src.budget import BatchBudget
from src.crawl.fetcher import fetch_url


def test_fetch_url_respects_budget():
    budget = BatchBudget(max_requests=0)  # Exhausted

    with patch("src.crawl.fetcher._get_robots_parser") as mock_rp:
        rp = MagicMock()
        rp.can_fetch.return_value = True
        mock_rp.return_value = rp

        import pytest

        from src.budget import BudgetExceeded

        with pytest.raises(BudgetExceeded):
            fetch_url("https://example.com", budget)
