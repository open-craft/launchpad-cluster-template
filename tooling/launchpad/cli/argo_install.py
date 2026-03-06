"""
Argo install commands for ArgoCD and Argo Workflows.
"""

import argparse
import subprocess

from launchpad.cli.utils import exit_with_error, run_command_with_logging
from launchpad.config import ClusterConfig, get_config
from launchpad.exceptions import (
    CommandNotFoundError,
    ConfigurationError,
    KubernetesError,
    ManifestError,
    PasswordError,
)
from launchpad.kubeconfig import setup_kubeconfig
from launchpad.kubernetes import DEFAULT_DOCKER_PULL_SECRET_NAME, KubernetesClient
from launchpad.password import (
    bcrypt_password,
    get_password_mtime,
    resolve_plaintext_password,
)
from launchpad.utils import get_logger, log_success

logger = get_logger(__name__)

SYSTEM_NAMESPACES = {
    "kube-system",
    "kube-public",
    "kube-node-lease",
}


def _is_system_namespace(namespace: str) -> bool:
    return namespace in SYSTEM_NAMESPACES or namespace.startswith("kube-")


def _configure_registry_pull_secrets(
    k8s: KubernetesClient,
    cluster_config: ClusterConfig,
    namespaces: list[str],
    *,
    scan_existing_namespaces: bool = False,
    secret_name: str = DEFAULT_DOCKER_PULL_SECRET_NAME,
) -> None:
    """
    Configure image pull credentials for one or more namespaces, and optionally best-effort for all.
    """
    auth = (cluster_config.docker_registry_credentials or "").strip()
    if not auth:
        logger.info(
            "LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS not set; skipping cluster-wide registry credentials"
        )
        return

    registry = cluster_config.docker_registry

    for ns in namespaces:
        k8s.ensure_namespace_registry_credentials(
            namespace=ns,
            registry=registry,
            auth=auth,
            secret_name=secret_name,
        )

    if not scan_existing_namespaces:
        return

    # Best-effort: configure credentials for all existing non-system namespaces.
    # This covers instances created before this feature existed.
    for ns in k8s.list_namespaces():
        if ns in namespaces or _is_system_namespace(ns):
            continue
        try:
            k8s.ensure_namespace_registry_credentials(
                namespace=ns,
                registry=registry,
                auth=auth,
                secret_name=secret_name,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Failed to configure registry pull secret in namespace '%s': %s", ns, e
            )


def _apply_argo_workflows_template(url: str, namespace: str) -> None:
    """
    Apply an Argo Workflows template using kubectl.

    Args:
        url: URL of the template manifest
        namespace: Namespace to apply to

    Raises:
        KubernetesError: If applying the template fails
    """
    try:
        result = subprocess.run(
            ["kubectl", "apply", "-f", url, "-n", namespace],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            if not ("already exists" in result.stderr or "409" in result.stderr):
                raise KubernetesError(
                    f"Failed to apply Argo Workflows template: {result.stderr}"
                )

            logger.warning("Template already exists, skipping creation")

    except subprocess.CalledProcessError as e:
        raise KubernetesError(f"Failed to apply Argo Workflows template: {e}") from e
    except Exception as e:
        raise KubernetesError(
            f"Unexpected error applying Argo Workflows template: {e}"
        ) from e


def _install_argo_workflows_templates(cluster_config: ClusterConfig) -> None:
    """
    Install Argo Workflows templates for provisioning/deprovisioning.

    Args:
        cluster_config: Cluster configuration
    """
    manifests_url = cluster_config.opencraft_manifests_url

    templates = [
        "launchpad-mysql-provision-template.yml",
        "launchpad-mongodb-provision-template.yml",
        "launchpad-storage-provision-template.yml",
        "launchpad-mysql-deprovision-template.yml",
        "launchpad-mongodb-deprovision-template.yml",
        "launchpad-storage-deprovision-template.yml",
    ]

    for template in templates:
        template_name = template.replace(".yml", "").replace("-template", "")
        run_command_with_logging(
            logger,
            f"install {template_name} template",
            _apply_argo_workflows_template,
            f"{manifests_url}/{template}",
            "argo",
        )

    log_success(logger, "Argo Workflows templates installed successfully")


def install_argo_workflows(cluster_config: ClusterConfig) -> None:
    """
    Install Argo Workflows in the Kubernetes cluster.

    Args:
        cluster_config: Cluster configuration with Argo Workflows settings

    Raises:
        CommandNotFoundError: If required commands are not installed
        ConfigurationError: If required configuration is missing
        KubernetesError: If Kubernetes operations fail
        ManifestError: If manifest operations fail
    """

    k8s = KubernetesClient()

    run_command_with_logging(
        logger,
        "create Argo Workflows namespace",
        k8s.create_namespace,
        "argo",
    )

    run_command_with_logging(
        logger,
        "install Argo Workflows core components",
        k8s.apply_manifest_from_url,
        cluster_config.argo_workflows_install_url,
        "argo",
    )

    run_command_with_logging(
        logger,
        "create workflow-executor token in argo namespace",
        k8s.apply_manifest,
        """apiVersion: v1
kind: Secret
metadata:
  name: workflow-executor-token
  namespace: argo
  annotations:
    kubernetes.io/service-account.name: workflow-executor
type: kubernetes.io/service-account-token""",
        "argo",
    )

    _install_argo_workflows_templates(cluster_config)

    run_command_with_logging(
        logger,
        "configure cluster-wide docker registry pull credentials",
        _configure_registry_pull_secrets,
        k8s,
        cluster_config,
        ["argo", "default"],
        scan_existing_namespaces=True,
    )

    log_success(logger, "Argo Workflows installed successfully")


def install_argocd(cluster_config: ClusterConfig) -> None:
    """
    Install ArgoCD in the Kubernetes cluster.

    Args:
        cluster_config: Cluster configuration with ArgoCD settings

    Raises:
        CommandNotFoundError: If required commands are not installed
        ConfigurationError: If required configuration is missing
        KubernetesError: If Kubernetes operations fail
        ManifestError: If manifest operations fail
        PasswordError: If password operations fail
    """

    k8s = KubernetesClient()

    generated_password = not cluster_config.argo_admin_password
    plaintext_password = resolve_plaintext_password(cluster_config.argo_admin_password)

    run_command_with_logging(
        logger,
        "create ArgoCD namespace",
        k8s.create_namespace,
        "argocd",
    )

    run_command_with_logging(
        logger,
        "install ArgoCD core components",
        k8s.apply_manifest_from_url,
        cluster_config.argocd_install_url,
        "argocd",
    )

    run_command_with_logging(
        logger,
        "ensure base ArgoCD configmap",
        k8s.apply_manifest_from_url,
        f"{cluster_config.opencraft_manifests_url}/argocd-base-config.yml",
        "argocd",
    )

    run_command_with_logging(
        logger,
        "ensure ArgoCD server role allows web terminal (pods/exec)",
        k8s.ensure_role_has_pods_exec,
        "argocd-server",
        "argocd",
    )

    run_command_with_logging(
        logger,
        "configure ArgoCD ingress",
        k8s.apply_manifest_from_url,
        f"{cluster_config.opencraft_manifests_url}/argocd-ingress.yml",
        "argocd",
        {
            "LAUNCHPAD_CLUSTER_DOMAIN": cluster_config.cluster_domain,
        },
    )

    run_command_with_logging(
        logger,
        "configure ArgoCD admin password",
        k8s.apply_manifest_from_url,
        f"{cluster_config.opencraft_manifests_url}/argocd-admin-password.yml",
        "argocd",
        {
            "LAUNCHPAD_CLUSTER_DOMAIN": cluster_config.cluster_domain,
            "LAUNCHPAD_ARGO_ADMIN_PASSWORD_BCRYPT": bcrypt_password(plaintext_password),
            "LAUNCHPAD_ARGOCD_ADMIN_PASSWORD_MTIME": get_password_mtime(),
        },
    )

    run_command_with_logging(
        logger,
        "configure docker registry pull credentials in argocd namespace",
        _configure_registry_pull_secrets,
        k8s,
        cluster_config,
        ["argocd"],
        scan_existing_namespaces=False,
    )

    if generated_password:
        logger.warning(
            "Generated Argo admin password (store securely): %s", plaintext_password
        )

    log_success(logger, "ArgoCD installed successfully")


def main():
    """
    Main entry point for argo install command.
    """

    parser = argparse.ArgumentParser(
        description="Install ArgoCD and Argo Workflows in a Kubernetes cluster"
    )
    parser.add_argument(
        "--argocd-only",
        action="store_true",
        help="Install only ArgoCD",
    )
    parser.add_argument(
        "--workflows-only",
        action="store_true",
        help="Install only Argo Workflows",
    )

    args = parser.parse_args()

    setup_kubeconfig()

    try:
        config = get_config()
        install_both = not args.argocd_only and not args.workflows_only

        if install_both or args.argocd_only:
            logger.info("Installing ArgoCD...")
            install_argocd(config.cluster)

        if install_both or args.workflows_only:
            logger.info("Installing Argo Workflows...")
            install_argo_workflows(config.cluster)
    except (
        CommandNotFoundError,
        ConfigurationError,
        KubernetesError,
        ManifestError,
        PasswordError,
    ) as e:
        exit_with_error(logger, f"Installation failed: {e}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        exit_with_error(logger, f"Unexpected error: {e}", exc_info=False)
