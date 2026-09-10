"""Corporate compliance, governance structure, and automated risk pre-screening for Norwegian entities."""
from __future__ import annotations

from typing import Any


def evaluate_compliance(profile: dict[str, Any]) -> dict[str, Any]:
    """Evaluate corporate governance, statutory compliance, and operational risk for a company profile."""
    flags: list[dict[str, str]] = []
    risk_score = 10  # Baseline low-risk score for verified entities
    
    ev = profile.get("evidence", {})
    reg_live = (ev.get("registry_live", {}).get("value") or {}) if isinstance(ev.get("registry_live"), dict) else {}
    roles_data = (ev.get("roles", {}).get("value") or {}) if isinstance(ev.get("roles"), dict) else {}
    acct_ob = (ev.get("accounting_obligation", {}).get("value") or {}) if isinstance(ev.get("accounting_obligation"), dict) else {}
    fin_data = (ev.get("financials", {}).get("value") or {}) if isinstance(ev.get("financials"), dict) else {}
    
    # 1. Insolvency / Adverse State Checks
    is_bankrupt = bool(reg_live.get("bankrupt") or profile.get("bankrupt"))
    is_liquidating = bool(reg_live.get("liquidating") or profile.get("liquidating"))
    
    if is_bankrupt:
        risk_score += 80
        flags.append({
            "code": "BANKRUPTCY_REGISTERED",
            "severity": "critical",
            "message": "Company is registered as bankrupt (konkurs) in the Register of Business Enterprises.",
        })
    elif is_liquidating:
        risk_score += 50
        flags.append({
            "code": "LIQUIDATION_IN_PROGRESS",
            "severity": "high",
            "message": "Company is in liquidation or compulsory dissolution (under avvikling).",
        })

    # 2. Statutory Accounting Compliance
    legal_form = str(profile.get("legal_form") or reg_live.get("legal_form") or "").upper()
    has_records = bool(fin_data.get("records"))
    acct_class = acct_ob.get("classification")
    
    if legal_form in {"AS", "ASA"} and not has_records:
        risk_score += 25
        flags.append({
            "code": "MISSING_MANDATORY_ACCOUNTS",
            "severity": "medium",
            "message": f"Statutory annual accounts not reported for mandatory legal form {legal_form}.",
        })

    # 3. Governance and Leadership Oversight
    roles_list = roles_data.get("roles", []) if isinstance(roles_data, dict) else []
    has_chair = False
    has_ceo = False
    for r in roles_list:
        role_code = str(r.get("role_code") or "").upper()
        role_name = str(r.get("role") or "").casefold()
        if "leder" in role_name or "styreleder" in role_name or role_code in {"STYR", "LEDE"}:
            has_chair = True
        if "daglig leder" in role_name or role_code == "DAGL":
            has_ceo = True

    if legal_form in {"AS", "ASA"} and not has_chair and roles_list:
        risk_score += 15
        flags.append({
            "code": "NO_BOARD_CHAIR",
            "severity": "low",
            "message": "No registered board chair (styreleder) found in active leadership records.",
        })

    # 4. Overall Rating Assignment
    risk_score = min(100, max(0, risk_score))
    if risk_score <= 25:
        compliance_tier = "low_risk"
        status_label = "Verified / Low Risk"
        badge_color = "green"
    elif risk_score <= 50:
        compliance_tier = "medium_risk"
        status_label = "Monitoring / Standard Diligence"
        badge_color = "amber"
    else:
        compliance_tier = "high_risk"
        status_label = "High Risk / Action Required"
        badge_color = "red"

    return {
        "compliance_tier": compliance_tier,
        "status_label": status_label,
        "badge_color": badge_color,
        "risk_score": risk_score,
        "flags_count": len(flags),
        "flags": flags,
        "governance": {
            "has_board_chair": has_chair,
            "has_managing_director": has_ceo,
            "total_registered_officers": len(roles_list),
        },
        "statutory_filings": {
            "accounting_obligated": legal_form in {"AS", "ASA"} or acct_class == "filing_observed",
            "financial_statements_available": has_records,
        },
    }
