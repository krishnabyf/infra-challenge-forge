from __future__ import annotations

import ipaddress
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
}


def load_manifests(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    files = sorted(path.rglob("*.yaml")) + sorted(path.rglob("*.yml"))
    documents: list[dict[str, Any]] = []
    for file in files:
        documents.extend(doc for doc in yaml.safe_load_all(file.read_text()) if doc)
    return documents

