# Incident Brief

At 16:42 UTC, a production deployment used an image that differed from the
artifact tested in staging. The release failed health checks, but the workflow
had no rollback job. During response, the team found repository secrets holding
long-lived AWS keys, one administrator role shared across staging and
production, and Terraform state in an unversioned bucket without locking.

Recover the delivery system without weakening account separation or bypassing
production approval.

## Your work

1. Replace AWS access-key secrets with GitHub OIDC.
2. Restrict role trust to this repository and the `staging` or `production`
   GitHub environment.
3. Create separate one-hour deployment roles in the staging and production
   accounts.
4. Attach a permissions boundary to every deployment role.
5. Replace wildcard deployment permissions with resource-scoped ECS, ECR,
   CloudWatch, and `iam:PassRole` access.
6. Protect Terraform state with S3 versioning, KMS encryption, complete public
   access blocking, and a DynamoDB `LockID` table with point-in-time recovery.
7. Configure the workflow with minimal OIDC permissions.
8. Build once, capture the image digest, deploy that same digest to staging,
   and promote it to production.
9. Require a production plan, successful staging deployment, production
   environment approval, and deployment concurrency.
10. Verify production health and automatically restore the previous ECS task
    definition when verification fails.

## Constraints

- Do not store AWS credentials in GitHub secrets.
- Do not use `AdministratorAccess` or wildcard actions. Wildcard resources are
  allowed only for AWS APIs that do not support resource-level authorization,
  and those exceptions must be isolated in their own policy statement.
- Do not let staging credentials operate in production.
- Do not rebuild the image between staging and production.
- Do not disable health checks to make deployment pass.
- Terraform remains the source of truth for trust, IAM, and state controls.

## Submission inputs

The evaluator reads:

- `terraform show -json plan.out` from your repaired Terraform.
- The repaired workflow directory containing `deploy.yml`.

The pass threshold is 80/100. Identity and state controls account for 60 points
because compromise or state corruption can affect every later deployment.
