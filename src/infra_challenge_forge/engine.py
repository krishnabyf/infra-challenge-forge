from __future__ import annotations

import json
from pathlib import Path

from .checks import CHECKS, load_manifests
from .models import Challenge, Finding, Report


def evaluate(challenge: Challenge, plan_path: Path, manifests_path: Path | None) -> Report:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    manifests = load_manifests(manifests_path)
    findings: list[Finding] = []
    for rule in challenge.rules:
        check = CHECKS.get(rule.check)
        if check is None:
            raise ValueError(f"unknown check: {rule.check}")
        passed, evidence = check(plan, manifests, rule.params)
        findings.append(
            Finding(
                rule_id=rule.id,
                title=rule.title,
                category=rule.category,
                passed=passed,
                weight=rule.weight,
                evidence=evidence,
            )
        )
    return Report(
        challenge_id=challenge.id,
        score=sum(item.weight for item in findings if item.passed),
        max_score=challenge.total_weight,
        passing_score=challenge.passing_score,
        findings=tuple(findings),
    )

