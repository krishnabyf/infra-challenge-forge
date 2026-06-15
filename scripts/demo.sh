#!/usr/bin/env bash
set -euo pipefail

scenario="challenges/eks-incident-response"

echo "1/2 Proving the compromised starter is rejected"
if .venv/bin/infra-forge evaluate "$scenario/challenge.yaml" \
  --plan "$scenario/fixtures/insecure-plan.json" \
  --manifests "$scenario/starter/kubernetes"; then
  echo "ERROR: insecure fixture unexpectedly passed"
  exit 1
else
  status=$?
  if [[ "$status" -ne 2 ]]; then
    exit "$status"
  fi
fi

echo
echo "2/2 Proving the remediated reference reaches 100/100"
.venv/bin/infra-forge evaluate "$scenario/challenge.yaml" \
  --plan "$scenario/fixtures/secure-plan.json" \
  --manifests "$scenario/reference/kubernetes" \
  --output report.json

