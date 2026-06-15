# Threat Model

## Protected assets

- Cloud credentials used by an optional live evaluation stage
- Integrity of challenge scores
- Availability and cost boundaries of evaluation accounts
- Confidentiality of hidden tests and reference solutions

## Primary threats

| Threat | Control |
| --- | --- |
| Candidate code executes on the runner | Core engine only parses JSON and YAML |
| Terraform provisioner escapes isolation | Candidate Terraform is planned in a disposable sandbox; plan JSON is the evaluator input |
| Over-privileged CI identity | OIDC role with session policy, no stored AWS keys |
| Resource exhaustion or cloud spend | Job timeout, quotas, budget alarm, SCP, independent cleanup |
| Rule gaming through HCL formatting | Evaluate normalized plan values |
| False confidence from one happy fixture | Known-bad and known-good regression fixtures |
| Hidden-test disclosure | Keep private evaluation packs outside candidate clones |

## Residual risk

Terraform providers and YAML parsers process attacker-controlled input and may
contain vulnerabilities. Production evaluators should pin dependencies, scan the
runner image, use an unprivileged container, disable outbound network where
possible, and discard the runner after each submission.

