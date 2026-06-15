# Infrastructure Challenge Forge

[![CI](https://github.com/krishnabyf/infra-challenge-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/krishnabyf/infra-challenge-forge/actions/workflows/ci.yml)

Infrastructure Challenge Forge is an executable evaluation system for senior
DevOps, SRE, platform engineering, and AI infrastructure reasoning tasks. It
scores the resulting infrastructure, not superficial HCL patterns.

The included challenge starts from a real incident shape: a compromised pod,
wildcard AWS permissions, an internet-reachable EKS API, incomplete audit
signals, public workload placement, and weak Kubernetes isolation. The candidate
must recover the platform while preserving service availability.

## What this proves

- Terraform plan analysis across networking, EKS, KMS, IAM, and failure domains
- Weighted, evidence-producing infrastructure evaluation
- Kubernetes security, zero-trust networking, and disruption resilience
- Fail-closed CI that proves the bad solution fails and the reference passes
- Safe evaluator design that does not execute candidate-controlled hooks
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

## First challenge

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

## Repository map

```text
src/infra_challenge_forge/      scoring engine and rule implementations
challenges/
  eks-incident-response/
    starter/                    deliberately vulnerable candidate baseline
    reference/                  remediated Terraform and Kubernetes solution
    fixtures/                   deterministic Terraform plan regression data
    challenge.yaml              machine-readable weighted rubric
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

