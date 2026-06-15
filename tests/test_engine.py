from pathlib import Path

from infra_challenge_forge.engine import evaluate
from infra_challenge_forge.models import load_challenge

ROOT = Path(__file__).parents[1]
SCENARIO = ROOT / "challenges" / "eks-incident-response"
CHALLENGE = load_challenge(SCENARIO / "challenge.yaml")


def test_reference_solution_passes_every_rule() -> None:
    report = evaluate(
        CHALLENGE,
        SCENARIO / "fixtures" / "secure-plan.json",
        SCENARIO / "reference" / "kubernetes",
    )
    assert report.score == 100
    assert report.passed
    assert all(finding.passed for finding in report.findings)


def test_starter_is_rejected_with_actionable_findings() -> None:
    report = evaluate(
        CHALLENGE,
        SCENARIO / "fixtures" / "insecure-plan.json",
        SCENARIO / "starter" / "kubernetes",
    )
    assert report.score < report.passing_score
    assert not report.passed
    assert {f.rule_id for f in report.findings if not f.passed} >= {
        "NET-002",
        "EKS-001",
        "IAM-001",
        "K8S-001",
    }


def test_rubric_is_normalized() -> None:
    assert CHALLENGE.total_weight == 100
    assert len({rule.id for rule in CHALLENGE.rules}) == len(CHALLENGE.rules)

