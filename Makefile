.PHONY: install lint test evaluate demo clean

install:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

lint:
	.venv/bin/ruff check src tests

test:
	.venv/bin/pytest

evaluate:
	.venv/bin/infra-forge evaluate challenges/eks-incident-response/challenge.yaml \
		--plan challenges/eks-incident-response/fixtures/secure-plan.json \
		--manifests challenges/eks-incident-response/reference/kubernetes

demo:
	./scripts/demo.sh

clean:
	rm -rf .venv .pytest_cache .ruff_cache report.json

