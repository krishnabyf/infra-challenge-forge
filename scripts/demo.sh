#!/usr/bin/env bash
set -euo pipefail

eks_scenario="challenges/eks-incident-response"
cicd_scenario="challenges/multi-account-cicd-recovery"

echo "1/4 Proving the compromised EKS starter is rejected"
if .venv/bin/infra-forge evaluate "$eks_scenario/challenge.yaml" \
  --plan "$eks_scenario/fixtures/insecure-plan.json" \
  --manifests "$eks_scenario/starter/kubernetes"; then
  echo "ERROR: insecure fixture unexpectedly passed"
  exit 1
else
  status=$?
  if [[ "$status" -ne 2 ]]; then
    exit "$status"
  fi
fi

echo
echo "2/4 Proving the remediated EKS reference reaches 100/100"
.venv/bin/infra-forge evaluate "$eks_scenario/challenge.yaml" \
  --plan "$eks_scenario/fixtures/secure-plan.json" \
  --manifests "$eks_scenario/reference/kubernetes" \
  --output report.json

echo
echo "3/4 Proving the insecure multi-account pipeline is rejected"
if .venv/bin/infra-forge evaluate "$cicd_scenario/challenge.yaml" \
  --plan "$cicd_scenario/fixtures/insecure-plan.json" \
  --manifests "$cicd_scenario/starter/workflows"; then
  echo "ERROR: insecure CI/CD fixture unexpectedly passed"
  exit 1
else
  status=$?
  if [[ "$status" -ne 2 ]]; then
    exit "$status"
  fi
fi

echo
echo "4/4 Proving the recovered multi-account pipeline reaches 100/100"
.venv/bin/infra-forge evaluate "$cicd_scenario/challenge.yaml" \
  --plan "$cicd_scenario/fixtures/secure-plan.json" \
  --manifests "$cicd_scenario/reference/workflows" \
  --output cicd-report.json
