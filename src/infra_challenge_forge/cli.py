from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import evaluate
from .models import load_challenge


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="infra-forge")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("evaluate", help="score a Terraform plan and manifests")
    command.add_argument("challenge", type=Path)
    command.add_argument("--plan", required=True, type=Path)
    command.add_argument("--manifests", type=Path)
    command.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    challenge = load_challenge(args.challenge)
    report = evaluate(challenge, args.plan, args.manifests)
    payload = report.as_dict()
    if args.output:
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    status = "PASS" if report.passed else "FAIL"
    print(f"{status} {report.score}/{report.max_score} (threshold {report.passing_score})")
    for finding in report.findings:
        marker = "PASS" if finding.passed else "FAIL"
        print(f"[{marker}] {finding.rule_id} ({finding.weight}): {finding.evidence}")
    return 0 if report.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

