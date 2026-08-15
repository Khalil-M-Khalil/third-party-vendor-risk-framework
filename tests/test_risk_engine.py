import pandas as pd
import pytest

from src.risk_engine import ScoringConfig, portfolio_metrics, score_assessment, validate_inputs


@pytest.fixture
def fixtures():
    vendors = pd.DataFrame([
        {
            "vendor_id": "V-TEST",
            "vendor_name": "Test Vendor",
            "service_type": "SaaS",
            "criticality": "critical",
            "data_classification": "restricted",
            "internet_exposure": "public",
            "privileged_access": "admin",
            "geography": "multi_region",
            "financial_dependency": "critical",
            "continuity_dependency": "critical",
        }
    ])
    questions = pd.DataFrame([
        {"question_id": "Q-01", "domain": "Identity", "question_text": "MFA?", "weight": 1.0, "reference_area": "NIST"},
        {"question_id": "Q-02", "domain": "Resilience", "question_text": "Recovery tested?", "weight": 1.0, "reference_area": "NIST"},
    ])
    answers = pd.DataFrame([
        {"vendor_id": "V-TEST", "question_id": "Q-01", "answer": "yes", "evidence_status": "documented", "owner": "Identity", "remediation": "Maintain evidence"},
        {"vendor_id": "V-TEST", "question_id": "Q-02", "answer": "no", "evidence_status": "missing", "owner": "Continuity", "remediation": "Run recovery test"},
    ])
    return vendors, questions, answers


def test_scoring_is_explainable(fixtures):
    register, findings = score_assessment(*fixtures)
    row = register.iloc[0]
    assert row["inherent_score"] == pytest.approx(94.4)
    assert row["control_effectiveness_percent"] == pytest.approx(50.0)
    assert row["residual_score"] == pytest.approx(73.16)
    assert row["risk_tier"] == "High"
    assert int(row["open_gaps"]) == 1
    assert len(findings) == 2


def test_mitigation_factor_changes_residual_risk(fixtures):
    register, _ = score_assessment(*fixtures, ScoringConfig(mitigation_factor=0.0))
    assert register.iloc[0]["residual_score"] == pytest.approx(register.iloc[0]["inherent_score"])


def test_portfolio_metrics(fixtures):
    register, _ = score_assessment(*fixtures)
    metrics = portfolio_metrics(register)
    assert metrics["vendors"] == 1
    assert metrics["critical_high"] == 1
    assert metrics["tier_counts"]["High"] == 1


def test_missing_question_is_rejected(fixtures):
    vendors, questions, answers = fixtures
    broken = answers.copy()
    broken.loc[0, "question_id"] = "Q-404"
    with pytest.raises(ValueError, match="Every answer question_id"):
        score_assessment(vendors, questions, broken)


def test_duplicate_vendor_is_rejected(fixtures):
    vendors, questions, answers = fixtures
    broken = pd.concat([vendors, vendors], ignore_index=True)
    with pytest.raises(ValueError, match="vendor_id values must be unique"):
        validate_inputs(broken, questions)
