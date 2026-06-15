# Changelog

All notable changes to Infrastructure Challenge Forge are documented here.

## [0.2.0] - 2026-06-15

### Added

- Multi-account AWS CI/CD recovery challenge.
- GitHub OIDC trust and static-credential detection.
- Deployment-role permissions-boundary and policy-scope checks.
- Hardened S3/KMS Terraform state and DynamoDB locking checks.
- Workflow checks for account separation, production gates, immutable image
  promotion, health verification, and failure-only rollback.
- Candidate workbench with repair and verification commands.
- `actionlint` and provider-backed Terraform validation in CI.
- `infra-forge --version` command.

### Changed

- Demo now proves both insecure starters fail and both references score 100/100.
- GitHub Actions run on the Node 24 runtime.

## [0.1.0] - 2026-06-15

### Added

- Initial evaluator CLI and weighted challenge specification.
- EKS incident-response challenge covering networking, IAM, KMS, security,
  observability, reliability, and Kubernetes workload controls.
- Docker image, regression fixtures, tests, documentation, and GitHub Actions.

[0.2.0]: https://github.com/krishnabyf/infra-challenge-forge/releases/tag/v0.2.0
[0.1.0]: https://github.com/krishnabyf/infra-challenge-forge/releases/tag/v0.1.0
