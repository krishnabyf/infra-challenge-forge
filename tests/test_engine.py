from pathlib import Path

from infra_challenge_forge.engine import evaluate
from infra_challenge_forge.models import load_challenge

ROOT = Path(__file__).parents[1]
EKS_SCENARIO = ROOT / "challenges" / "eks-incident-response"
EKS_CHALLENGE = load_challenge(EKS_SCENARIO / "challenge.yaml")
CICD_SCENARIO = ROOT / "challenges" / "multi-account-cicd-recovery"
CICD_CHALLENGE = load_challenge(CICD_SCENARIO / "challenge.yaml")


def test_reference_solution_passes_every_rule() -> None:
    report = evaluate(
        EKS_CHALLENGE,
        EKS_SCENARIO / "fixtures" / "secure-plan.json",
        EKS_SCENARIO / "reference" / "kubernetes",
    )
    assert report.score == 100
    assert report.passed
    assert all(finding.passed for finding in report.findings)


def test_starter_is_rejected_with_actionable_findings() -> None:
    report = evaluate(
        EKS_CHALLENGE,
        EKS_SCENARIO / "fixtures" / "insecure-plan.json",
        EKS_SCENARIO / "starter" / "kubernetes",
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
    for challenge in (EKS_CHALLENGE, CICD_CHALLENGE):
        assert challenge.total_weight == 100
        assert len({rule.id for rule in challenge.rules}) == len(challenge.rules)


def test_multi_account_reference_passes_every_rule() -> None:
    report = evaluate(
        CICD_CHALLENGE,
        CICD_SCENARIO / "fixtures" / "secure-plan.json",
        CICD_SCENARIO / "reference" / "workflows",
    )
    assert report.score == 100
    assert report.passed
    assert all(finding.passed for finding in report.findings)


def test_multi_account_starter_is_rejected_with_actionable_findings() -> None:
    report = evaluate(
        CICD_CHALLENGE,
        CICD_SCENARIO / "fixtures" / "insecure-plan.json",
        CICD_SCENARIO / "starter" / "workflows",
    )
    assert report.score < report.passing_score
    assert not report.passed
    assert {finding.rule_id for finding in report.findings if not finding.passed} >= {
        "OIDC-001",
        "OIDC-002",
        "IAM-101",
        "STATE-001",
        "STATE-002",
        "PIPE-005",
    }
