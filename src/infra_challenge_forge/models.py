from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    category: str
    check: str
    weight: int
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Challenge:
    id: str
    title: str
    passing_score: int
    rules: tuple[Rule, ...]

    @property
    def total_weight(self) -> int:
        return sum(rule.weight for rule in self.rules)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    category: str
    passed: bool
    weight: int
    evidence: str


@dataclass(frozen=True)
class Report:
    challenge_id: str
    score: int
    max_score: int
    passing_score: int
    findings: tuple[Finding, ...]

    @property
    def passed(self) -> bool:
        return self.score >= self.passing_score

    def as_dict(self) -> dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "score": self.score,
            "max_score": self.max_score,
            "passing_score": self.passing_score,
            "passed": self.passed,
            "findings": [
                {
                    "rule_id": item.rule_id,
                    "title": item.title,
                    "category": item.category,
                    "passed": item.passed,
                    "weight": item.weight,
                    "evidence": item.evidence,
                }
                for item in self.findings
            ],
        }


def load_challenge(path: Path) -> Challenge:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules = tuple(
        Rule(
            id=item["id"],
            title=item["title"],
            category=item["category"],
            check=item["check"],
            weight=int(item["weight"]),
            params=item.get("params", {}),
        )
        for item in data["rules"]
    )
    challenge = Challenge(
        id=data["id"],
        title=data["title"],
        passing_score=int(data["passing_score"]),
        rules=rules,
    )
    if challenge.total_weight != 100:
        raise ValueError(f"challenge weights must total 100, got {challenge.total_weight}")
    if len({rule.id for rule in rules}) != len(rules):
        raise ValueError("rule IDs must be unique")
    return challenge

