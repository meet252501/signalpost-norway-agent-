import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.compliance import evaluate_compliance
from norway_company_agent.financial_analysis import analyze_financial_health, calculate_ratios


class TestFinancialAnalysis(unittest.TestCase):
    def test_calculate_ratios_healthy_company(self):
        record = {
            "assets": 10_000_000.0,
            "equity": 5_000_000.0,
            "debt": 5_000_000.0,
            "revenue": 12_000_000.0,
            "operating_result": 2_000_000.0,
            "annual_result": 1_500_000.0,
        }
        res = calculate_ratios(record)
        self.assertEqual(res["equity_ratio_pct"], 50.0)
        self.assertEqual(res["debt_to_equity"], 1.0)
        self.assertEqual(res["operating_margin_pct"], 16.67)
        self.assertEqual(res["net_profit_margin_pct"], 12.5)
        self.assertEqual(res["solvency_status"], "solid")
        self.assertIsNotNone(res["altman_z_score"])
        self.assertEqual(res["credit_risk_tier"], "low_risk")

    def test_calculate_ratios_distressed_company(self):
        record = {
            "assets": 5_000_000.0,
            "equity": -1_000_000.0,
            "debt": 6_000_000.0,
            "revenue": 1_000_000.0,
            "operating_result": -800_000.0,
            "annual_result": -900_000.0,
        }
        res = calculate_ratios(record)
        self.assertEqual(res["equity_ratio_pct"], -20.0)
        self.assertEqual(res["solvency_status"], "negative_equity")
        self.assertEqual(res["credit_risk_tier"], "high_risk")

    def test_calculate_ratios_zero_division_safe(self):
        record = {
            "assets": 0.0,
            "equity": 0.0,
            "debt": 0.0,
            "revenue": 0.0,
            "operating_result": 0.0,
            "annual_result": 0.0,
        }
        res = calculate_ratios(record)
        self.assertIsNone(res["equity_ratio_pct"])
        self.assertEqual(res["credit_risk_tier"], "unknown")
        self.assertEqual(res["solvency_status"], "insufficient_data")

    def test_analyze_financial_health_multi_year_trend(self):
        profile = {
            "evidence": {
                "financials": {
                    "value": {
                        "records": [
                            {
                                "assets": 12_000_000.0,
                                "equity": 6_000_000.0,
                                "revenue": 15_000_000.0,
                                "operating_result": 2_000_000.0,
                            },
                            {
                                "assets": 10_000_000.0,
                                "equity": 4_000_000.0,
                                "revenue": 10_000_000.0,
                                "operating_result": 1_000_000.0,
                            },
                        ]
                    }
                }
            }
        }
        res = analyze_financial_health(profile)
        self.assertTrue(res["has_financials"])
        self.assertEqual(res["revenue_trend"], "growing")
        self.assertEqual(len(res["history"]), 2)
        self.assertEqual(res["latest"]["equity_ratio_pct"], 50.0)

    def test_analyze_financial_health_empty(self):
        res = analyze_financial_health({})
        self.assertEqual(res["status"], "not_available")
        self.assertFalse(res["has_financials"])


class TestCompliance(unittest.TestCase):
    def test_clean_company_compliance(self):
        profile = {
            "organisation_number": "123456789",
            "name": "NORDIC TECH AS",
            "legal_form": "AS",
            "evidence": {
                "registry_live": {"value": {"bankrupt": False, "liquidating": False}},
                "financials": {"value": {"records": [{"revenue": 5000000}]}},
                "roles": {
                    "value": {
                        "roles": [
                            {"role": "Styreleder", "role_code": "STYR"},
                            {"role": "Daglig leder", "role_code": "DAGL"},
                        ]
                    }
                },
            },
        }
        comp = evaluate_compliance(profile)
        self.assertEqual(comp["compliance_tier"], "low_risk")
        self.assertEqual(comp["flags_count"], 0)
        self.assertTrue(comp["governance"]["has_board_chair"])
        self.assertTrue(comp["governance"]["has_managing_director"])

    def test_bankrupt_company_compliance(self):
        profile = {
            "organisation_number": "999888777",
            "name": "FAILED VENTURE AS",
            "legal_form": "AS",
            "bankrupt": True,
            "evidence": {},
        }
        comp = evaluate_compliance(profile)
        self.assertEqual(comp["compliance_tier"], "high_risk")
        self.assertGreaterEqual(comp["risk_score"], 80)
        self.assertTrue(any(f["code"] == "BANKRUPTCY_REGISTERED" for f in comp["flags"]))

    def test_missing_accounts_warning(self):
        profile = {
            "organisation_number": "555444333",
            "name": "LATE FILER AS",
            "legal_form": "AS",
            "evidence": {
                "financials": {"value": {"records": []}},
            },
        }
        comp = evaluate_compliance(profile)
        self.assertTrue(any(f["code"] == "MISSING_MANDATORY_ACCOUNTS" for f in comp["flags"]))


class TestResearchAnswering(unittest.TestCase):
    def test_answer_profile_health_and_compliance(self):
        from norway_company_agent.research import answer_profile

        profile = {
            "organisation_number": "123456789",
            "name": "NORDIC TECH AS",
            "financial_health": {
                "altman_z_score": 3.45,
                "credit_tier": "Low Default Risk",
                "solvency_status": "Solid",
                "equity_ratio_pct": 52.4,
                "financial_trend": "Growing",
            },
            "compliance": {
                "compliance_rating": "LOW RISK",
                "sanctions_screening": "CLEAR",
                "risk_score": 10,
                "board_governance": "VERIFIED",
                "flags": [],
            },
            "evidence": {
                "registry": {"status": "available"},
                "financials": {"status": "available"},
            },
        }

        # Query health
        health_ans = answer_profile(profile, "What is the financial health and solvency?")
        claims = {f["claim"]: f["value"] for f in health_ans["facts"]}
        self.assertEqual(claims.get("Altman Z''-Score"), 3.45)
        self.assertEqual(claims.get("Credit risk tier"), "Low Default Risk")
        self.assertEqual(claims.get("Solvency status"), "Solid")

        # Query compliance
        comp_ans = answer_profile(profile, "Is there any AML or KYC compliance risk?")
        comp_claims = {f["claim"]: f["value"] for f in comp_ans["facts"]}
        self.assertEqual(comp_claims.get("AML/KYC compliance rating"), "LOW RISK")
        self.assertEqual(comp_claims.get("Sanctions screening status"), "CLEAR")


if __name__ == "__main__":
    unittest.main()

