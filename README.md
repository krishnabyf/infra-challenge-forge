# Infrastructure Challenge Forge

[![CI](https://github.com/krishnabyf/infra-challenge-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/krishnabyf/infra-challenge-forge/actions/workflows/ci.yml)

Infrastructure Challenge Forge is an executable evaluation system for senior
DevOps, SRE, platform engineering, and AI infrastructure reasoning tasks. It
scores the resulting infrastructure, not superficial HCL patterns.

The included challenges start from real incident shapes: a compromised EKS
workload and a failed multi-account production release backed by long-lived AWS
keys, shared administrator access, unsafe Terraform state, and no rollback.

## What this proves

- Terraform plan analysis across networking, EKS, KMS, IAM, and failure domains
- Weighted, evidence-producing infrastructure evaluation
- Kubernetes security, zero-trust networking, and disruption resilience
- Fail-closed CI that proves the bad solution fails and the reference passes
- Safe evaluator design that does not execute candidate-controlled hooks
- Multi-account GitHub OIDC, permissions boundaries, state locking, and rollback
- Clear challenge-authoring, architecture, and threat-model documentation

## Run it

```bash
make install
make lint
make test
make demo
```

Expected final line:

```text
PASS 100/100 (threshold 80)
```

Evaluate a real Terraform plan:

```bash
terraform plan -out plan.out
terraform show -json plan.out > plan.json

infra-forge evaluate \
  challenges/eks-incident-response/challenge.yaml \
  --plan plan.json \
  --manifests ./kubernetes \
  --output report.json
```

The CLI returns exit code `0` for a passing submission, `2` for a scored failure,
and a non-scoring error for invalid configuration.

## Challenge catalog

### 1. EKS incident response

| Category | Examples | Weight |
| --- | --- | ---: |
| Networking | Private subnets, ingress boundaries, VPC DNS | 25 |
| EKS security and telemetry | Private API, CIDRs, complete logs | 25 |
| Data protection and IAM | KMS secrets encryption, least privilege | 25 |
| Reliability | AZ-local NAT, probes, replicas, PDB | 10 |
| Kubernetes security | Non-root, immutable filesystem, default deny | 15 |

Read the candidate brief in
[`challenges/eks-incident-response/prompt.md`](challenges/eks-incident-response/prompt.md)
and the evaluator rationale in [`docs/architecture.md`](docs/architecture.md).

### 2. Multi-account CI/CD recovery

| Category | Examples | Weight |
| --- | --- | ---: |
| Federated identity | GitHub OIDC trust, no static AWS keys | 25 |
| IAM blast radius | Boundaries, scoped policy, isolated account roles | 25 |
| Terraform state | S3 recovery controls, KMS, DynamoDB locking | 25 |
| Pipeline safety | Minimal permissions, account binding, gates | 15 |
| Release recovery | Immutable digest promotion, rollback validation | 10 |

Start with the exact work checklist in
[`challenges/multi-account-cicd-recovery/WORK.md`](challenges/multi-account-cicd-recovery/WORK.md).
The candidate incident brief is in
[`challenges/multi-account-cicd-recovery/prompt.md`](challenges/multi-account-cicd-recovery/prompt.md).

## Repository map

```text
src/infra_challenge_forge/      scoring engine and rule implementations
challenges/
  eks-incident-response/
    starter/                    deliberately vulnerable candidate baseline
    reference/                  remediated Terraform and Kubernetes solution
    fixtures/                   deterministic Terraform plan regression data
    challenge.yaml              machine-readable weighted rubric
  multi-account-cicd-recovery/
    starter/                    static-key, shared-role, no-rollback baseline
    reference/                  OIDC, bounded IAM, locked state, safe promotion
    WORK.md                     exact candidate tasks and verification commands
docs/                           architecture, authoring guide, threat model
tests/                          evaluator regression tests
```

## Production extension path

The next layer is a disposable-account runner: accept a submission archive,
create an isolated work directory, run `terraform plan` with a read-only OIDC
identity, feed plan JSON to this engine, optionally deploy approved fixtures into
a short-lived account, run behavioral probes, and tear down with an independent
cleanup role. The core repository deliberately keeps that trust boundary
separate.

## License

MIT
