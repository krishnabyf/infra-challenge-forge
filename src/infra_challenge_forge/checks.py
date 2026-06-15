from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path
from typing import Any, Callable

import yaml

Check = Callable[[dict[str, Any], list[dict[str, Any]], dict[str, Any]], tuple[bool, str]]


def resources(plan: dict[str, Any], resource_type: str) -> list[dict[str, Any]]:
    root = plan.get("planned_values", {}).get("root_module", {})
    pending = [root]
    found: list[dict[str, Any]] = []
    while pending:
        module = pending.pop()
        found.extend(r for r in module.get("resources", []) if r.get("type") == resource_type)
        pending.extend(module.get("child_modules", []))
    return found


def _values(plan: dict[str, Any], resource_type: str) -> list[dict[str, Any]]:
    return [item.get("values", {}) for item in resources(plan, resource_type)]


def vpc_dns(plan: dict[str, Any], _: list[dict[str, Any]], __: dict[str, Any]) -> tuple[bool, str]:
    vpcs = _values(plan, "aws_vpc")
    passed = bool(vpcs) and all(v.get("enable_dns_support") and v.get("enable_dns_hostnames") for v in vpcs)
    return passed, f"{len(vpcs)} VPC(s); DNS support and hostnames must both be enabled"


def private_subnets(plan: dict[str, Any], _: list[dict[str, Any]], __: dict[str, Any]) -> tuple[bool, str]:
    subnets = _values(plan, "aws_subnet")
    private = [s for s in subnets if s.get("tags", {}).get("Tier") == "private"]
    passed = len(private) >= 2 and all(not s.get("map_public_ip_on_launch", False) for s in private)
    return passed, f"{len(private)} private subnet(s); require at least two without public IP assignment"


def restricted_ingress(plan: dict[str, Any], _: list[dict[str, Any]], __: dict[str, Any]) -> tuple[bool, str]:
    groups = _values(plan, "aws_security_group")
    bad: list[str] = []
    for group in groups:
        for ingress in group.get("ingress", []) or []:
            cidrs = ingress.get("cidr_blocks", []) or []
            if "0.0.0.0/0" in cidrs and ingress.get("from_port", 0) != 443:
                bad.append(group.get("name", "unnamed"))
    return not bad and bool(groups), f"unrestricted non-HTTPS ingress groups: {bad or 'none'}"


def private_cluster_endpoint(
    plan: dict[str, Any], _: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    clusters = _values(plan, "aws_eks_cluster")
    passed = bool(clusters) and all(
        c.get("vpc_config")
        and c["vpc_config"][0].get("endpoint_private_access")
        and not c["vpc_config"][0].get("endpoint_public_access")
        for c in clusters
    )
    return passed, "EKS API must be private-only"


def control_plane_logs(
    plan: dict[str, Any], _: list[dict[str, Any]], params: dict[str, Any]
) -> tuple[bool, str]:
    required = set(params.get("required", []))
    clusters = _values(plan, "aws_eks_cluster")
    actual = set(clusters[0].get("enabled_cluster_log_types", [])) if clusters else set()
    missing = sorted(required - actual)
    return not missing and bool(clusters), f"missing control-plane logs: {missing or 'none'}"


def secrets_encryption(
    plan: dict[str, Any], _: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    clusters = _values(plan, "aws_eks_cluster")
    encrypted = [
        c
        for c in clusters
        if c.get("encryption_config")
        and "secrets" in c["encryption_config"][0].get("resources", [])
        and c["encryption_config"][0].get("provider", [{}])[0].get("key_arn")
    ]
    return len(encrypted) == len(clusters) and bool(clusters), "KMS envelope encryption required for secrets"


def least_privilege_iam(
    plan: dict[str, Any], _: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    policies = _values(plan, "aws_iam_policy")
    wildcards: list[str] = []
    for policy in policies:
        document = policy.get("policy")
        if isinstance(document, str):
            if '"Action":"*"' in document.replace(" ", "") or '"Resource":"*"' in document.replace(" ", ""):
                wildcards.append(policy.get("name", "unnamed"))
    return not wildcards and bool(policies), f"policies with wildcard action/resource: {wildcards or 'none'}"


def nat_per_az(plan: dict[str, Any], _: list[dict[str, Any]], __: dict[str, Any]) -> tuple[bool, str]:
    nat_gateways = _values(plan, "aws_nat_gateway")
    private_subnet_values = [
        s for s in _values(plan, "aws_subnet") if s.get("tags", {}).get("Tier") == "private"
    ]
    azs = {s.get("availability_zone") for s in private_subnet_values}
    return len(nat_gateways) >= len(azs) >= 2, f"{len(nat_gateways)} NAT gateway(s) for {len(azs)} private AZ(s)"


def no_public_cidrs(plan: dict[str, Any], _: list[dict[str, Any]], __: dict[str, Any]) -> tuple[bool, str]:
    clusters = _values(plan, "aws_eks_cluster")
    public: list[str] = []
    for cluster in clusters:
        for config in cluster.get("vpc_config", []) or []:
            for cidr in config.get("public_access_cidrs", []) or []:
                if ipaddress.ip_network(cidr).prefixlen == 0:
                    public.append(cidr)
    return not public and bool(clusters), f"world-routable API CIDRs: {public or 'none'}"


def workload_security(
    _: dict[str, Any], manifests: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    deployments = [m for m in manifests if m.get("kind") == "Deployment"]
    bad: list[str] = []
    for deployment in deployments:
        pod = deployment.get("spec", {}).get("template", {}).get("spec", {})
        pod_context = pod.get("securityContext", {})
        containers = pod.get("containers", [])
        secure = (
            pod_context.get("runAsNonRoot") is True
            and containers
            and all(
                c.get("securityContext", {}).get("readOnlyRootFilesystem") is True
                and c.get("securityContext", {}).get("allowPrivilegeEscalation") is False
                and c.get("resources", {}).get("requests")
                and c.get("resources", {}).get("limits")
                for c in containers
            )
        )
        if not secure:
            bad.append(deployment.get("metadata", {}).get("name", "unnamed"))
    return bool(deployments) and not bad, f"insecure deployments: {bad or 'none'}"


def workload_resilience(
    _: dict[str, Any], manifests: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    deployments = [m for m in manifests if m.get("kind") == "Deployment"]
    pdbs = [m for m in manifests if m.get("kind") == "PodDisruptionBudget"]
    bad: list[str] = []
    for deployment in deployments:
        spec = deployment.get("spec", {})
        containers = spec.get("template", {}).get("spec", {}).get("containers", [])
        if spec.get("replicas", 0) < 2 or not all(
            c.get("readinessProbe") and c.get("livenessProbe") for c in containers
        ):
            bad.append(deployment.get("metadata", {}).get("name", "unnamed"))
    return bool(deployments) and bool(pdbs) and not bad, (
        f"non-resilient deployments: {bad or 'none'}; PDB count: {len(pdbs)}"
    )


def network_policy(
    _: dict[str, Any], manifests: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    policies = [m for m in manifests if m.get("kind") == "NetworkPolicy"]
    default_deny = any(
        not p.get("spec", {}).get("podSelector", {}).get("matchLabels")
        and {"Ingress", "Egress"}.issubset(set(p.get("spec", {}).get("policyTypes", [])))
        for p in policies
    )
    return default_deny, f"{len(policies)} NetworkPolicy object(s); default deny ingress+egress required"


def _json_document(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _statements(document: dict[str, Any]) -> list[dict[str, Any]]:
    statements = document.get("Statement", [])
    if isinstance(statements, dict):
        return [statements]
    return [item for item in statements if isinstance(item, dict)]


def github_oidc_trust(
    plan: dict[str, Any], _: list[dict[str, Any]], params: dict[str, Any]
) -> tuple[bool, str]:
    providers = _values(plan, "aws_iam_openid_connect_provider")
    roles = _values(plan, "aws_iam_role")
    repository = params.get("repository", "")
    environments = set(params.get("environments", []))
    trusted_environments: set[str] = set()
    audience_restricted = False

    for role in roles:
        document = _json_document(role.get("assume_role_policy"))
        for statement in _statements(document):
            condition = statement.get("Condition", {})
            values = json.dumps(condition, sort_keys=True)
            audience_restricted |= (
                "token.actions.githubusercontent.com:aud" in values
                and "sts.amazonaws.com" in values
            )
            for environment in environments:
                subject = f"repo:{repository}:environment:{environment}"
                if subject in values:
                    trusted_environments.add(environment)

    provider_ok = any(
        item.get("url") == "https://token.actions.githubusercontent.com"
        and "sts.amazonaws.com" in (item.get("client_id_list") or [])
        for item in providers
    )
    missing = sorted(environments - trusted_environments)
    passed = provider_ok and audience_restricted and not missing
    return passed, (
        f"OIDC provider: {'present' if provider_ok else 'missing'}; "
        f"untrusted environments: {missing or 'none'}"
    )


def no_static_aws_keys(
    plan: dict[str, Any], manifests: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    access_keys = _values(plan, "aws_iam_access_key")
    workflow_text = yaml.safe_dump(manifests).lower()
    key_references = sorted(
        {
            name
            for name in ("aws_access_key_id", "aws_secret_access_key", "aws_session_token")
            if name in workflow_text
        }
    )
    passed = not access_keys and not key_references
    return passed, (
        f"IAM access key resources: {len(access_keys)}; "
        f"static credential references: {key_references or 'none'}"
    )


def deployment_permissions_boundaries(
    plan: dict[str, Any], _: list[dict[str, Any]], params: dict[str, Any]
) -> tuple[bool, str]:
    required_accounts = set(params.get("accounts", []))
    roles = [
        role
        for role in _values(plan, "aws_iam_role")
        if role.get("tags", {}).get("Purpose") == "deployment"
    ]
    bounded_accounts = {
        role.get("tags", {}).get("Account")
        for role in roles
        if role.get("permissions_boundary")
    }
    missing = sorted(required_accounts - bounded_accounts)
    return bool(roles) and not missing, (
        f"deployment roles: {len(roles)}; accounts missing boundaries: {missing or 'none'}"
    )


def deployment_policy_scope(
    plan: dict[str, Any], _: list[dict[str, Any]], params: dict[str, Any]
) -> tuple[bool, str]:
    allowed_wildcard_actions = set(params.get("allowed_wildcard_resource_actions", []))
    policies = [
        policy
        for policy in _values(plan, "aws_iam_policy")
        if policy.get("tags", {}).get("Purpose") == "deployment"
    ]
    violations: list[str] = []
    for policy in policies:
        document = _json_document(policy.get("policy"))
        for statement in _statements(document):
            actions = statement.get("Action", [])
            resources_value = statement.get("Resource", [])
            actions = [actions] if isinstance(actions, str) else actions
            resource_arns = (
                [resources_value] if isinstance(resources_value, str) else resources_value
            )
            wildcard_action = "*" in actions
            invalid_wildcard_resource = "*" in resource_arns and not set(actions).issubset(
                allowed_wildcard_actions
            )
            if wildcard_action or invalid_wildcard_resource:
                violations.append(policy.get("name", "unnamed"))
                break
    return bool(policies) and not violations, (
        f"deployment policies with wildcard action/resource: {violations or 'none'}"
    )


def isolated_deployment_roles(
    plan: dict[str, Any], _: list[dict[str, Any]], params: dict[str, Any]
) -> tuple[bool, str]:
    required_accounts = set(params.get("accounts", []))
    roles = [
        role
        for role in _values(plan, "aws_iam_role")
        if role.get("tags", {}).get("Purpose") == "deployment"
    ]
    accounts = {role.get("tags", {}).get("Account") for role in roles}
    long_sessions = [
        role.get("name", "unnamed")
        for role in roles
        if int(role.get("max_session_duration", 43200)) > 3600
    ]
    missing = sorted(required_accounts - accounts)
    passed = not missing and not long_sessions and len(roles) >= len(required_accounts)
    return passed, (
        f"missing account roles: {missing or 'none'}; "
        f"roles over one-hour sessions: {long_sessions or 'none'}"
    )


def hardened_state_backend(
    plan: dict[str, Any], _: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    buckets = [
        item
        for item in _values(plan, "aws_s3_bucket")
        if item.get("tags", {}).get("Purpose") == "terraform-state"
    ]
    versions = _values(plan, "aws_s3_bucket_versioning")
    encryption = _values(plan, "aws_s3_bucket_server_side_encryption_configuration")
    public_blocks = _values(plan, "aws_s3_bucket_public_access_block")
    kms_keys = _values(plan, "aws_kms_key")

    versioned = any(
        item.get("versioning_configuration", [{}])[0].get("status") == "Enabled"
        for item in versions
    )
    kms_encrypted = any(
        rule.get("apply_server_side_encryption_by_default", [{}])[0].get("sse_algorithm")
        == "aws:kms"
        for item in encryption
        for rule in (item.get("rule") or [])
    )
    public_blocked = any(
        all(
            item.get(key) is True
            for key in (
                "block_public_acls",
                "block_public_policy",
                "ignore_public_acls",
                "restrict_public_buckets",
            )
        )
        for item in public_blocks
    )
    key_rotation = any(item.get("enable_key_rotation") is True for item in kms_keys)
    controls = {
        "bucket": bool(buckets),
        "versioning": versioned,
        "kms": kms_encrypted,
        "public-block": public_blocked,
        "key-rotation": key_rotation,
    }
    missing = sorted(name for name, enabled in controls.items() if not enabled)
    return not missing, f"missing state controls: {missing or 'none'}"


def state_locking(
    plan: dict[str, Any], _: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    tables = _values(plan, "aws_dynamodb_table")
    valid = [
        table
        for table in tables
        if table.get("hash_key") == "LockID"
        and table.get("billing_mode") == "PAY_PER_REQUEST"
        and any(
            attribute.get("name") == "LockID" and attribute.get("type") == "S"
            for attribute in (table.get("attribute") or [])
        )
        and table.get("point_in_time_recovery", [{}])[0].get("enabled") is True
    ]
    return bool(valid), (
        f"valid LockID tables: {len(valid)}; require on-demand billing and PITR"
    )


def _workflow_jobs(manifests: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    for document in manifests:
        jobs = document.get("jobs")
        if isinstance(jobs, dict):
            return document, jobs
    return {}, {}


def workflow_oidc_permissions(
    _: dict[str, Any], manifests: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    workflow, _ = _workflow_jobs(manifests)
    permissions = workflow.get("permissions", {})
    valid = (
        permissions.get("id-token") == "write"
        and permissions.get("contents") == "read"
        and set(permissions) <= {"id-token", "contents"}
    )
    return valid, f"workflow permissions: {permissions or 'missing'}"


def workflow_account_separation(
    _: dict[str, Any], manifests: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    _, jobs = _workflow_jobs(manifests)
    expected = {"deploy-staging": "staging", "deploy-production": "production"}
    role_arns: dict[str, str] = {}
    missing: list[str] = []
    for job_name, environment in expected.items():
        job = jobs.get(job_name, {})
        if job.get("environment") != environment:
            missing.append(f"{job_name}:environment")
        text = yaml.safe_dump(job)
        match = re.search(r"arn:aws:iam::(\d{12}):role/[A-Za-z0-9+=,.@_/-]+", text)
        if match:
            role_arns[job_name] = match.group(0)
        else:
            missing.append(f"{job_name}:role")
    distinct = len(set(role_arns.values())) == len(expected)
    return not missing and distinct, (
        f"missing deployment bindings: {missing or 'none'}; distinct roles: {distinct}"
    )


def workflow_production_gate(
    _: dict[str, Any], manifests: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    workflow, jobs = _workflow_jobs(manifests)
    production = jobs.get("deploy-production", {})
    needs = production.get("needs", [])
    needs = [needs] if isinstance(needs, str) else needs
    concurrency = workflow.get("concurrency") or production.get("concurrency")
    gated = (
        production.get("environment") == "production"
        and "plan-production" in needs
        and "deploy-staging" in needs
        and bool(concurrency)
    )
    return gated, (
        f"production needs: {needs or 'none'}; "
        f"environment: {production.get('environment', 'missing')}; "
        f"concurrency: {'set' if concurrency else 'missing'}"
    )


def workflow_immutable_release(
    _: dict[str, Any], manifests: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    _, jobs = _workflow_jobs(manifests)
    build = yaml.safe_dump(jobs.get("build", {}))
    deployments = yaml.safe_dump(
        {
            name: jobs.get(name, {})
            for name in ("deploy-staging", "deploy-production")
        }
    )
    produces_digest = "digest" in build and "outputs" in build
    consumes_digest = "needs.build.outputs.digest" in deployments
    mutable_latest = ":latest" in deployments
    return produces_digest and consumes_digest and not mutable_latest, (
        f"build digest output: {produces_digest}; deployments consume digest: "
        f"{consumes_digest}; mutable latest tag: {mutable_latest}"
    )


def workflow_rollback_validation(
    _: dict[str, Any], manifests: list[dict[str, Any]], __: dict[str, Any]
) -> tuple[bool, str]:
    _, jobs = _workflow_jobs(manifests)
    verify = jobs.get("verify-production", {})
    rollback = jobs.get("rollback-production", {})
    verify_text = yaml.safe_dump(verify).lower()
    rollback_text = yaml.safe_dump(rollback).lower()
    rollback_needs = rollback.get("needs", [])
    rollback_needs = [rollback_needs] if isinstance(rollback_needs, str) else rollback_needs
    health_check = "/health" in verify_text or "/ready" in verify_text
    failure_only = "failure()" in str(rollback.get("if", ""))
    restores_previous = "previous" in rollback_text and (
        "task-definition" in rollback_text or "rollback" in rollback_text
    )
    linked = "verify-production" in rollback_needs
    passed = health_check and failure_only and restores_previous and linked
    return passed, (
        f"health verification: {health_check}; failure-only rollback: {failure_only}; "
        f"previous revision restore: {restores_previous}; linked to verification: {linked}"
    )


CHECKS: dict[str, Check] = {
    "vpc_dns": vpc_dns,
    "private_subnets": private_subnets,
    "restricted_ingress": restricted_ingress,
    "private_cluster_endpoint": private_cluster_endpoint,
    "control_plane_logs": control_plane_logs,
    "secrets_encryption": secrets_encryption,
    "least_privilege_iam": least_privilege_iam,
    "nat_per_az": nat_per_az,
    "no_public_cidrs": no_public_cidrs,
    "workload_security": workload_security,
    "workload_resilience": workload_resilience,
    "network_policy": network_policy,
    "github_oidc_trust": github_oidc_trust,
    "no_static_aws_keys": no_static_aws_keys,
    "deployment_permissions_boundaries": deployment_permissions_boundaries,
    "deployment_policy_scope": deployment_policy_scope,
    "isolated_deployment_roles": isolated_deployment_roles,
    "hardened_state_backend": hardened_state_backend,
    "state_locking": state_locking,
    "workflow_oidc_permissions": workflow_oidc_permissions,
    "workflow_account_separation": workflow_account_separation,
    "workflow_production_gate": workflow_production_gate,
    "workflow_immutable_release": workflow_immutable_release,
    "workflow_rollback_validation": workflow_rollback_validation,
}


def load_manifests(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    files = sorted(path.rglob("*.yaml")) + sorted(path.rglob("*.yml"))
    documents: list[dict[str, Any]] = []
    for file in files:
        documents.extend(doc for doc in yaml.safe_load_all(file.read_text()) if doc)
    return documents
