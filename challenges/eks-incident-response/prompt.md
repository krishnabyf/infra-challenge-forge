# Incident Brief

At 09:14 UTC, the detection team observed calls to AWS APIs from a pod in the
`payments` namespace. The pod had obtained credentials with broad permissions.
The EKS API was reachable from the internet, audit logging was incomplete, and
two workloads shared a permissive network path.

You own the recovery. Repair the supplied Terraform and Kubernetes configuration
without changing the application image or removing required service-to-service
communication.

## Required outcome

- Preserve a three-AZ VPC and private workload placement.
- Make the EKS control plane private and enable all control-plane log types.
- Encrypt Kubernetes secrets with a customer-managed KMS key.
- Replace wildcard IAM with the minimum DynamoDB and KMS permissions.
- Prevent a single NAT gateway failure from removing egress in every AZ.
- Run workloads as non-root with immutable filesystems and bounded resources.
- Add health probes, at least two replicas, a disruption budget, and default-deny
  namespace networking.

## Constraints

- Terraform remains the source of truth.
- Do not use provisioners, local-exec, static AWS credentials, or public node IPs.
- Do not weaken a control simply to make a test pass.
- The evaluator consumes `terraform show -json plan.out` plus Kubernetes YAML.

## Submission

```bash
terraform init
terraform plan -out plan.out
terraform show -json plan.out > plan.json
infra-forge evaluate challenge.yaml --plan plan.json --manifests kubernetes --output report.json
```

The pass threshold is 80/100. IAM least privilege and private workload placement
are deliberately high-weight because they materially reduce incident blast radius.

