"""Financial health, solvency ratios, and credit risk evaluation for Norwegian corporations."""
from __future__ import annotations

from typing import Any


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def calculate_ratios(record: dict[str, Any]) -> dict[str, Any]:
    """Calculate key financial ratios from a single normalized financial year record."""
    assets = _safe_float(record.get("assets"))
    equity = _safe_float(record.get("equity"))
    debt = _safe_float(record.get("debt"))
    revenue = _safe_float(record.get("revenue"))
    operating_result = _safe_float(record.get("operating_result"))
    annual_result = _safe_float(record.get("annual_result"))

    equity_ratio_pct = None
    if equity is not None and assets and assets > 0:
        equity_ratio_pct = round((equity / assets) * 100.0, 2)

    debt_to_equity = None
    if debt is not None and equity and equity > 0:
        debt_to_equity = round(debt / equity, 2)

    operating_margin_pct = None
    if operating_result is not None and revenue and revenue > 0:
        operating_margin_pct = round((operating_result / revenue) * 100.0, 2)

    net_profit_margin_pct = None
    if annual_result is not None and revenue and revenue > 0:
        net_profit_margin_pct = round((annual_result / revenue) * 100.0, 2)

    return_on_assets_pct = None
    if annual_result is not None and assets and assets > 0:
        return_on_assets_pct = round((annual_result / assets) * 100.0, 2)

    # Altman Z''-Score for private unlisted / emerging service firms:
    # Z'' = 6.56 * X1 + 3.26 * X2 + 6.72 * X3 + 1.05 * X4
    # Where:
    # X1 = Working Capital / Total Assets (approximated from Equity & Debt balance)
    # X2 = Retained Earnings / Total Assets (approximated from Equity / Assets)
    # X3 = EBIT / Total Assets (Operating Result / Assets)
    # X4 = Book Value of Equity / Total Debt
    altman_z = None
    credit_risk_tier = "unknown"
    if assets and assets > 0 and equity is not None:
        x1 = max(-1.0, min(1.0, (equity - (debt or 0.0)) / assets))
        x2 = max(-1.0, min(1.0, equity / assets))
        x3 = (operating_result or 0.0) / assets
        x4 = (equity / (debt if debt and debt > 0 else 1.0))
        x4 = max(0.0, min(10.0, x4))
        
        raw_z = (6.56 * x1) + (3.26 * x2) + (6.72 * x3) + (1.05 * x4)
        altman_z = round(raw_z, 2)

        if altman_z >= 2.60:
            credit_risk_tier = "low_risk"  # Safe Zone
        elif altman_z >= 1.10:
            credit_risk_tier = "moderate_risk"  # Grey Zone
        else:
            credit_risk_tier = "high_risk"  # Distress Zone

    solvency_status = "insufficient_data"
    if equity_ratio_pct is not None:
        if equity_ratio_pct >= 40.0:
            solvency_status = "solid"
        elif equity_ratio_pct >= 20.0:
            solvency_status = "satisfactory"
        elif equity_ratio_pct > 0.0:
            solvency_status = "vulnerable"
        else:
            solvency_status = "negative_equity"

    return {
        "assets_nok": assets,
        "equity_nok": equity,
        "debt_nok": debt,
        "revenue_nok": revenue,
        "operating_result_nok": operating_result,
        "annual_result_nok": annual_result,
        "equity_ratio_pct": equity_ratio_pct,
        "debt_to_equity": debt_to_equity,
        "operating_margin_pct": operating_margin_pct,
        "net_profit_margin_pct": net_profit_margin_pct,
        "return_on_assets_pct": return_on_assets_pct,
        "altman_z_score": altman_z,
        "credit_risk_tier": credit_risk_tier,
        "solvency_status": solvency_status,
    }


def analyze_financial_health(evidence_source: dict[str, Any] | None) -> dict[str, Any]:
    """Extract and analyze financial health from a profile or financials evidence block."""
    if not evidence_source:
        return {"status": "not_available", "has_financials": False, "latest": None, "history": []}

    # Extract records list
    records: list[dict[str, Any]] = []
    if "value" in evidence_source and isinstance(evidence_source["value"], dict):
        records = evidence_source["value"].get("records", [])
    elif "evidence" in evidence_source and isinstance(evidence_source["evidence"], dict):
        fin = evidence_source["evidence"].get("financials", {})
        if isinstance(fin.get("value"), dict):
            records = fin["value"].get("records", [])
    elif "records" in evidence_source:
        records = evidence_source.get("records", [])

    if not records:
        return {
            "status": "not_available",
            "has_financials": False,
            "latest": None,
            "history": [],
            "rating_label": "No Filings Reported",
        }

    history = [calculate_ratios(rec) for rec in records]
    latest = history[0] if history else None

    # Trend detection if >= 2 years
    revenue_trend = "stable"
    if len(history) >= 2 and latest and latest.get("revenue_nok") is not None:
        prev_rev = history[1].get("revenue_nok")
        if prev_rev and prev_rev > 0:
            growth = ((latest["revenue_nok"] - prev_rev) / prev_rev) * 100.0
            if growth > 5.0:
                revenue_trend = "growing"
            elif growth < -5.0:
                revenue_trend = "declining"

    rating_label = "Unrated"
    if latest:
        tier = latest.get("credit_risk_tier")
        if tier == "low_risk":
            rating_label = "Prime / Low Risk (Safe Zone)"
        elif tier == "moderate_risk":
            rating_label = "Adequate / Moderate Risk (Grey Zone)"
        elif tier == "high_risk":
            rating_label = "Elevated Risk / Distress Watch"

    return {
        "status": "available",
        "has_financials": True,
        "latest": latest,
        "history": history,
        "revenue_trend": revenue_trend,
        "rating_label": rating_label,
    }
