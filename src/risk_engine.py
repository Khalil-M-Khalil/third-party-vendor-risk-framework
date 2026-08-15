"""Explainable third-party vendor risk scoring engine.

The model is a portfolio demonstration, not a certification or legal determination.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

STATUS_SCORES = {"yes": 1.0, "partial": 0.5, "no": 0.0, "na": None}
EVIDENCE_SCORES = {"documented": 1.0, "partial": 0.5, "missing": 0.0}
PRIORITY_ORDER = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
REQUIRED_VENDOR_COLUMNS = {
    "vendor_id", "vendor_name", "service_type", "criticality", "data_classification",
    "internet_exposure", "privileged_access", "geography", "financial_dependency",
    "continuity_dependency",
}
REQUIRED_QUESTION_COLUMNS = {"question_id", "domain", "question_text", "weight"}


@dataclass(frozen=True)
class ScoringConfig:
    """Weights and thresholds are intentionally visible for review and calibration."""

    criticality_weight: float = 0.24
    data_weight: float = 0.20
    privileged_weight: float = 0.16
    internet_weight: float = 0.12
    geography_weight: float = 0.08
    financial_weight: float = 0.08
    continuity_weight: float = 0.12
    mitigation_factor: float = 0.45


VENDOR_SCALE = {
    "criticality": {"low": 20, "medium": 50, "high": 80, "critical": 100},
    "data_classification": {"public": 10, "internal": 35, "confidential": 70, "restricted": 100},
    "internet_exposure": {"none": 0, "limited": 35, "direct": 80, "public": 100},
    "privileged_access": {"none": 0, "limited": 40, "admin": 85, "broad": 100},
    "geography": {"domestic": 25, "multi_region": 60, "high_risk_jurisdiction": 90},
    "financial_dependency": {"low": 20, "medium": 50, "high": 80, "critical": 100},
    "continuity_dependency": {"low": 20, "medium": 50, "high": 80, "critical": 100},
}


def _normalize(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_")


def validate_inputs(vendors: pd.DataFrame, questions: pd.DataFrame) -> None:
    missing_vendors = REQUIRED_VENDOR_COLUMNS.difference(vendors.columns)
    missing_questions = REQUIRED_QUESTION_COLUMNS.difference(questions.columns)
    if missing_vendors or missing_questions:
        raise ValueError(f"Missing columns: vendors={sorted(missing_vendors)}, questions={sorted(missing_questions)}")
    if vendors["vendor_id"].duplicated().any():
        raise ValueError("vendor_id values must be unique")
    if (questions["weight"] <= 0).any():
        raise ValueError("question weights must be positive")
    for field, scale in VENDOR_SCALE.items():
        invalid = sorted(set(_normalize(v) for v in vendors[field]) - set(scale))
        if invalid:
            raise ValueError(f"Invalid {field} values: {invalid}")


def _score_vendor_factors(row: pd.Series, config: ScoringConfig) -> dict[str, float]:
    factors = {
        "criticality_score": VENDOR_SCALE["criticality"][_normalize(row["criticality"])],
        "data_score": VENDOR_SCALE["data_classification"][_normalize(row["data_classification"])],
        "privileged_score": VENDOR_SCALE["privileged_access"][_normalize(row["privileged_access"])],
        "internet_score": VENDOR_SCALE["internet_exposure"][_normalize(row["internet_exposure"])],
        "geography_score": VENDOR_SCALE["geography"][_normalize(row["geography"])],
        "financial_score": VENDOR_SCALE["financial_dependency"][_normalize(row["financial_dependency"])],
        "continuity_score": VENDOR_SCALE["continuity_dependency"][_normalize(row["continuity_dependency"])],
    }
    weights = {
        "criticality_score": config.criticality_weight,
        "data_score": config.data_weight,
        "privileged_score": config.privileged_weight,
        "internet_score": config.internet_weight,
        "geography_score": config.geography_weight,
        "financial_score": config.financial_weight,
        "continuity_score": config.continuity_weight,
    }
    factors["inherent_score"] = sum(factors[key] * weight for key, weight in weights.items())
    return factors


def _tier(score: float) -> str:
    if score >= 75:
        return "Critical"
    if score >= 55:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def score_assessment(vendors: pd.DataFrame, questions: pd.DataFrame, answers: pd.DataFrame, config: ScoringConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return vendor register and normalized answer-level findings.

    Answers require vendor_id, question_id, answer, and evidence_status. Answer values are
    yes/partial/no/na; evidence values are documented/partial/missing.
    """
    config = config or ScoringConfig()
    validate_inputs(vendors, questions)
    required_answers = {"vendor_id", "question_id", "answer", "evidence_status", "owner", "remediation"}
    missing_answers = required_answers.difference(answers.columns)
    if missing_answers:
        raise ValueError(f"Missing answer columns: {sorted(missing_answers)}")

    q = questions.copy()
    q["question_id"] = q["question_id"].astype(str)
    a = answers.copy()
    a["answer"] = a["answer"].map(_normalize)
    a["evidence_status"] = a["evidence_status"].map(_normalize)
    invalid_answers = sorted(set(a["answer"]) - set(STATUS_SCORES))
    invalid_evidence = sorted(set(a["evidence_status"]) - set(EVIDENCE_SCORES))
    if invalid_answers or invalid_evidence:
        raise ValueError(f"Invalid answer values={invalid_answers}, evidence={invalid_evidence}")

    normalized = a.merge(q, on="question_id", how="left", validate="many_to_one")
    if normalized["question_text"].isna().any():
        raise ValueError("Every answer question_id must exist in the question bank")
    normalized["implementation_score"] = normalized["answer"].map(STATUS_SCORES)
    normalized["evidence_score"] = normalized["evidence_status"].map(EVIDENCE_SCORES)
    normalized["weighted_control_score"] = normalized["implementation_score"].fillna(0) * normalized["weight"]
    normalized["evidence_weighted_score"] = normalized["evidence_score"] * normalized["weight"]
    normalized["is_gap"] = normalized["answer"].isin({"no", "partial"})
    normalized["priority"] = normalized.apply(lambda r: "High" if r["answer"] == "no" else ("Medium" if r["answer"] == "partial" else "Low"), axis=1)

    rows: list[dict[str, object]] = []
    for _, vendor in vendors.iterrows():
        factors = _score_vendor_factors(vendor, config)
        vendor_answers = normalized[normalized["vendor_id"] == vendor["vendor_id"]]
        if vendor_answers.empty:
            control_effectiveness = 0.0
            evidence_coverage = 0.0
        else:
            denominator = vendor_answers["weight"].sum()
            control_effectiveness = vendor_answers["weighted_control_score"].sum() / denominator
            evidence_coverage = vendor_answers["evidence_weighted_score"].sum() / denominator
        control_effectiveness_pct = control_effectiveness * 100
        residual_score = factors["inherent_score"] * (1 - config.mitigation_factor * control_effectiveness)
        residual_score = min(100.0, max(0.0, residual_score))
        open_gaps = int(vendor_answers["is_gap"].sum())
        rows.append({
            "vendor_id": vendor["vendor_id"],
            "vendor_name": vendor["vendor_name"],
            "service_type": vendor["service_type"],
            "inherent_score": round(factors["inherent_score"], 2),
            "control_effectiveness_percent": round(control_effectiveness_pct, 2),
            "evidence_coverage_percent": round(evidence_coverage * 100, 2),
            "residual_score": round(residual_score, 2),
            "risk_tier": _tier(residual_score),
            "open_gaps": open_gaps,
            "recommended_review": "Monthly" if residual_score >= 75 else ("Quarterly" if residual_score >= 55 else "Semiannual"),
            **factors,
        })
    register = pd.DataFrame(rows).sort_values(["residual_score", "vendor_name"], ascending=[False, True]).reset_index(drop=True)
    normalized["risk_tier"] = normalized["vendor_id"].map(register.set_index("vendor_id")["risk_tier"])
    return register, normalized


def portfolio_metrics(register: pd.DataFrame) -> dict[str, object]:
    counts = register["risk_tier"].value_counts().to_dict()
    return {
        "vendors": int(len(register)),
        "critical_high": int(register["risk_tier"].isin({"Critical", "High"}).sum()),
        "average_residual_score": round(float(register["residual_score"].mean()), 2),
        "evidence_coverage": round(float(register["evidence_coverage_percent"].mean()), 2),
        "tier_counts": {tier: int(counts.get(tier, 0)) for tier in ["Critical", "High", "Medium", "Low"]},
    }
