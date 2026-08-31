from unittest.mock import MagicMock, patch

from src.budget import BatchBudget
from src.pipeline import process_company


@patch("src.pipeline.resolve_entity")
@patch("src.pipeline.fetch_url")
def test_process_company_basic(mock_fetch, mock_resolve):
    budget = BatchBudget()

    from src.validate.schema import Entity

    mock_entity = Entity(
        org_number="123",
        legal_name="Mock AS",
        status="active",
        website="mock.no",
        employee_count=150,
        latest_filed_accounts="2024",
    )
    mock_resolve.return_value = mock_entity

    # Mock fetch
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body>Some mock page</body></html>" + " " * 1000
    mock_fetch.return_value = mock_resp

    with (
        patch("src.pipeline.get_candidate_routes") as mock_routes,
        patch("src.pipeline.fetch_with_playwright") as mock_pw,
    ):
        mock_routes.return_value = {"careers": [], "about": []}
        mock_pw.return_value = None

        result = process_company("123", budget)

        assert result.status == "completed"
        assert result.profile.entity.org_number == "123"
        assert result.profile.official_site.value == "https://mock.no"
        assert result.profile.headcount_band.value == "51-200"
        assert result.profile.latest_filed_accounts.value == "2024"
