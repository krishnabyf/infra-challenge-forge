# Your Workbench

Use the Ubuntu repository:

```bash
cd /home/krishna/infra-challenge-forge
```

## Understand the failure

```bash
scenario=challenges/multi-account-cicd-recovery

.venv/bin/infra-forge evaluate "$scenario/challenge.yaml" \
  --plan "$scenario/fixtures/insecure-plan.json" \
  --manifests "$scenario/starter/workflows"
```

Read each failed rule and then inspect:

```bash
less "$scenario/prompt.md"
less "$scenario/starter/terraform/main.tf"
less "$scenario/starter/workflows/deploy.yml"
```

## Do the repair

Work only in a copy of `starter/`:

```bash
cp -R "$scenario/starter" /tmp/cicd-recovery-work
```

Your engineering tasks are:

- Terraform: OIDC provider, restricted trust policies, separate target-account
  roles, permission boundaries, scoped policies, state bucket controls, KMS key,
  and DynamoDB locking.
- GitHub Actions: OIDC permissions, separate staging/production roles,
  production environment gate, immutable digest promotion, health verification,
  and failure-only rollback.
- Documentation: record assumptions, account IDs, protected environments,
  rollback signal, and why each permission is required.

## Check your work

```bash
cd /tmp/cicd-recovery-work/terraform
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform plan -out plan.out \
  -var='tooling_account_id=111122223333' \
  -var='staging_account_id=444455556666' \
  -var='production_account_id=777788889999'
terraform show -json plan.out > ../plan.json

cd /home/krishna/infra-challenge-forge
.venv/bin/infra-forge evaluate \
  challenges/multi-account-cicd-recovery/challenge.yaml \
  --plan /tmp/cicd-recovery-work/plan.json \
  --manifests /tmp/cicd-recovery-work/workflows \
  --output /tmp/cicd-recovery-report.json
```

For a credential-free evaluator demonstration, compare the committed fixtures:

```bash
./scripts/demo.sh
```

## Evidence to explain in an interview

- Why OIDC `sub` conditions are restricted to GitHub environments.
- Why staging and production roles cannot be one shared role.
- What a permissions boundary limits and what it does not.
- Which AWS actions require `Resource: "*"` and why each exception is isolated.
- How S3 versioning and DynamoDB locking solve different state failure modes.
- Why image digest promotion is safer than rebuilding or using `latest`.
- Which health signal triggers rollback and which previous revision is restored.
- How GitHub environment reviewers and concurrency prevent unsafe production
  overlap.
