# Third-Party Vendor Risk Assessment Framework

A portfolio-grade Python framework for assessing cybersecurity and operational risk across third-party suppliers. It converts vendor context, security questionnaire answers, and evidence quality into an explainable risk register with inherent risk, control effectiveness, residual risk, tiering, remediation ownership, review cadence, and Excel/PDF outputs.

The repository is designed as a practical GRC demonstration. The vendors, answers, and findings are fictional. The tool supports risk-based prioritization; it is not a certification assessment, legal opinion, or substitute for procurement, security, privacy, or audit judgment.

## Why this project exists

Third-party risk is not limited to whether a vendor has a security badge or a current report. A defensible assessment connects the business relationship to the data handled, access granted, service dependency, geography, resilience expectations, evidence quality, and the organization’s ability to respond when controls fail.

This project demonstrates that lifecycle thinking in a compact, testable workflow. It can be used as a portfolio artifact, an interview discussion piece, or a starting point for a real vendor-risk operating model.

## Objectives

The framework answers five operational questions:

1. What is the supplier’s inherent exposure before considering controls?
2. How effective are the supplier controls represented by the assessment answers?
3. How much evidence supports those answers?
4. What is the resulting residual risk and vendor tier?
5. Who owns the remediation and when should the relationship be reviewed again?

## Methodology and framework alignment

The primary methodology lens is **NIST SP 800-161 Rev. 1**, *Cybersecurity Supply Chain Risk Management Practices for Systems and Organizations*. NIST describes the publication as guidance for identifying, assessing, and mitigating cybersecurity supply-chain risks at all organizational levels, integrating C-SCRM into risk-management activities through strategy, policies, plans, and risk assessments [1].

The project also incorporates the due-diligence themes published by NIST in its SP 1326 guidance, including supply-chain tiers, foreign ownership/control/influence, provenance, stability, and foundational cyber practices [2]. Because the official page currently marks SP 1326 as a later final publication, the README treats it as a supplemental due-diligence reference rather than a replacement for the core SP 800-161 Rev. 1 methodology.

The questionnaire domains are intentionally generic and **SIG-style**, including governance, data protection, identity and access, incident response, resilience, monitoring, vulnerability management, subcontractors, assurance, and exit/deletion. Shared Assessments describes SIG as a standardized questionnaire ecosystem that organizations can build, customize, analyze, and store for third-party risk management [3]. This project does not reproduce proprietary SIG question text or claim to be a licensed SIG implementation.

| Framework or practice | Use in this repository | Boundary |
| --- | --- | --- |
| NIST SP 800-161 Rev. 1 | Primary C-SCRM methodology lens and reference areas | The tool is an implementation example, not a complete NIST conformance assessment |
| NIST due diligence themes | Supplier context and foundational-practice considerations | Used as assessment themes, not reproduced publication text |
| SIG-style domains | Interoperable questionnaire organization | Generic labels only; no proprietary SIG content is copied |
| ISO/IEC 27001 | Not the primary framework in v1 | Can be added as a future crosswalk where licensed or public reference metadata is available |

## Risk model

The scoring model is explicit in `src/risk_engine.py` so that a reviewer can inspect, challenge, and calibrate every assumption.

### Inherent risk

Inherent risk is a weighted context score based on seven factors: business criticality, data classification, internet exposure, privileged access, geography, financial dependency, and continuity dependency. Each factor is normalized to a 0–100 scale, and the default weights sum to 100%.

> **Inherent risk = Σ(context factor score × factor weight)**

### Control effectiveness and evidence

Each question accepts `yes`, `partial`, `no`, or `na`. The default implementation mapping is Yes = 1.0, Partial = 0.5, No = 0.0, and Not Applicable is excluded from control effectiveness. Evidence is separately mapped as Documented = 1.0, Partial = 0.5, and Missing = 0.0. This separation avoids treating an unsupported “yes” answer as equivalent to a documented control.

### Residual risk

The default mitigation factor is 45%, which is intentionally visible and configurable. It models how much the assessed control effectiveness can reduce the inherent score:

> **Residual risk = inherent risk × (1 − mitigation factor × control effectiveness)**

The resulting score is capped at 0–100 and classified as follows:

| Residual score | Risk tier | Default review cadence |
| ---: | --- | --- |
| 75–100 | Critical | Monthly |
| 55–74.99 | High | Quarterly |
| 30–54.99 | Medium | Semiannual |
| 0–29.99 | Low | Semiannual |

These thresholds are portfolio assumptions, not universal industry limits. An operational program should calibrate them against risk appetite, critical services, regulatory obligations, contractual requirements, and incident history.

## Repository structure

```text
.
├── data/
│   ├── question_bank.csv
│   ├── vendor_answers.csv
│   └── vendor_profiles.csv
├── reports/
├── templates/
│   ├── question_bank_template.csv
│   ├── vendor_answer_template.csv
│   └── vendor_profile_template.csv
├── src/
│   └── risk_engine.py
├── tests/
│   └── test_risk_engine.py
├── vendor_risk.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Quick start

The project requires Python 3.10 or newer. Create an isolated environment, install dependencies, and run the CLI:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python vendor_risk.py
```

The command reads the default CSV files from `data/` and generates:

| Output | Purpose |
| --- | --- |
| `reports/vendor_risk_register.csv` | One row per vendor with inherent, effectiveness, evidence, residual, tier, and review data |
| `reports/vendor_assessment_findings.csv` | Question-level answer, evidence, owner, domain, and remediation detail |
| `reports/vendor_risk_assessment.xlsx` | Formatted workbook with Risk Register and Assessment Findings sheets |
| `reports/vendor_risk_assessment.pdf` | Compact management-ready risk register summary |

Custom input files and an alternative output directory can be supplied:

```bash
python vendor_risk.py \
  --vendors path/to/vendors.csv \
  --questions path/to/question_bank.csv \
  --answers path/to/answers.csv \
  --out-dir reports/custom
```

Run the tests with:

```bash
pytest
```

## Input contracts

The vendor file requires `vendor_id`, `vendor_name`, `service_type`, `criticality`, `data_classification`, `internet_exposure`, `privileged_access`, `geography`, `financial_dependency`, and `continuity_dependency`. The question bank requires `question_id`, `domain`, `question_text`, and `weight`. The answer file requires `vendor_id`, `question_id`, `answer`, `evidence_status`, `owner`, and `remediation`. The `templates/` directory provides blank starting points for the vendor profile, question bank, and answer files.

The engine validates unique vendor identifiers, positive question weights, allowed factor values, allowed answer values, and question IDs that exist in the question bank. Invalid inputs fail loudly rather than silently producing a misleading risk register.

## Demonstration results

The included dataset contains five fictional vendors across payment processing, HR SaaS, analytics, facilities, and backup/recovery. Running the default assessment generates a reproducible register and management report. Reviewers can inspect the question-level findings to see why a vendor is ranked above another rather than relying on a black-box score.

The sample data is intentionally fictional and contains no credentials, customer data, cloud credentials, real supplier attestations, or claims about actual companies. It is safe for local demonstration and repository review.

## Portfolio value

This project demonstrates practical GRC capabilities: supplier tiering, C-SCRM context modeling, questionnaire design, evidence-aware assessment, residual-risk calculation, remediation ownership, review cadence, CSV/Excel/PDF reporting, input validation, unit testing, and clear intellectual-property boundaries around proprietary questionnaires.

## Limitations and responsible use

The framework does not verify a supplier’s answers, independently test controls, interpret a contract, or issue an assurance conclusion. Evidence status is an input, not a guarantee of evidence authenticity. A production deployment should add authenticated users, approval workflows, immutable assessment history, data retention rules, evidence access controls, separation of duties, formal exception handling, and a documented risk-acceptance process.

The risk model is deliberately simple enough to explain in an interview. It should be calibrated before use in a real organization. Critical suppliers may require specialist review, legal input, privacy impact analysis, business continuity validation, architecture review, and ongoing monitoring beyond an annual questionnaire.

## Roadmap

Future versions can add a Streamlit review workspace, vendor lifecycle states, contract and renewal dates, risk acceptance workflow, evidence attachments, automated reminders, multi-framework crosswalk metadata, and integrations with procurement or GRC platforms. Those additions should preserve the current principle that every score is explainable and every remediation has an accountable owner.

## References

[1]: https://csrc.nist.gov/pubs/sp/800/161/r1/final "NIST SP 800-161 Rev. 1 — Cybersecurity Supply Chain Risk Management Practices for Systems and Organizations"

[2]: https://csrc.nist.gov/pubs/sp/1326/ipd "NIST SP 1326 — Cybersecurity Supply Chain Risk Management: Due Diligence Assessment Quick-Start Guide"

[3]: https://sharedassessments.org/sig/ "Shared Assessments — SIG Questionnaire"

## License

MIT. See `LICENSE` for the full text.
