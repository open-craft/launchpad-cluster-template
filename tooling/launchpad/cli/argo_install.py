"""
Argo install commands for ArgoCD and Argo Workflows.
"""

import subprocess

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import SettingsConfigDict

from launchpad.cli.utils import exit_with_error, run_command_with_logging
from launchpad.config import (
    ArgoAdminPasswordField,
    ArgocdGithubOauthClientIdField,
    ArgocdGithubOauthClientSecretField,
    ArgocdGithubOrgsField,
    ArgocdGithubSsoEnabledField,
    ArgocdInstallUrlMixin,
    ArgoWorkflowsInstallUrlMixin,
    ClusterDomainField,
    DockerRegistryCredentialsField,
    DockerRegistryField,
    LaunchpadBaseSettings,
    OpencraftManifestsUrlMixin,
)
from launchpad.exceptions import (
    CommandNotFoundError,
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
ARGOCD_NAMESPACE = "argocd"

DOCS_URL = (
    "https://github.com/open-craft/launchpad-cluster-template/blob/main/"
    "tooling/README.md#launchpad_install_argo"
)


class ArgoInstallSettings(
    LaunchpadBaseSettings,
    # Fields reused from ClusterConfig (see launchpad.config) -- only the
    # ones this command actually reads, composed from single-field mixins
    # so nothing unrelated (e.g. instances_directory, environment) leaks
    # into this command's --help output or config surface.
    ClusterDomainField,
    ArgocdInstallUrlMixin,
    ArgoWorkflowsInstallUrlMixin,
    OpencraftManifestsUrlMixin,
    DockerRegistryField,
    DockerRegistryCredentialsField,
    ArgoAdminPasswordField,
    ArgocdGithubSsoEnabledField,
    ArgocdGithubOauthClientIdField,
    ArgocdGithubOauthClientSecretField,
    ArgocdGithubOrgsField,
):
    __doc__ = f"""
    Configuration for `launchpad_install_argo`.

    Every option below can also be set via its matching LAUNCHPAD_<OPTION>
    environment variable (shown per option below, e.g. --argocd-version is
    LAUNCHPAD_ARGOCD_VERSION). CLI arguments take priority over environment
    variables, which take priority over the defaults shown below.

    Docs: {DOCS_URL}
    """

    model_config = SettingsConfigDict(
        env_prefix="LAUNCHPAD_",
        extra="forbid",
        frozen=True,
        cli_parse_args=True,
        cli_prog_name="launchpad_install_argo",
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_show_env_vars=True,
    )

    argocd_only: bool = Field(
        default=False,
        description="Install only ArgoCD, skip Argo Workflows.",
    )
    workflows_only: bool = Field(
        default=False,
        description="Install only Argo Workflows, skip ArgoCD.",
    )

    @model_validator(mode="after")
    def _validate_github_sso(self) -> "ArgoInstallSettings":
        """
        Ensure GitHub SSO settings are complete before any cluster work starts.
        """

        if not self.argocd_github_sso_enabled:
            return self

        client_id = self.argocd_github_oauth_client_id.strip()
        client_secret = self.argocd_github_oauth_client_secret.strip()
        github_orgs = self.argocd_github_orgs.strip()

        missing = []
        if not client_id:
            missing.append(
                "--argocd-github-oauth-client-id / LAUNCHPAD_ARGOCD_GITHUB_OAUTH_CLIENT_ID"
            )
        if not client_secret:
            missing.append(
                "--argocd-github-oauth-client-secret / "
                "LAUNCHPAD_ARGOCD_GITHUB_OAUTH_CLIENT_SECRET"
            )
        if not github_orgs:
            missing.append("--argocd-github-orgs / LAUNCHPAD_ARGOCD_GITHUB_ORGS")

        if missing:
            raise ValueError(
                "GitHub SSO is enabled, but required settings are missing: "
                + ", ".join(missing)
            )

        return self


def _is_system_namespace(namespace: str) -> bool:
    return namespace in SYSTEM_NAMESPACES or namespace.startswith("kube-")


def _split_csv_values(raw_value: str) -> list[str]:
    """
    Parse a comma-separated string into a list of non-empty trimmed values.
    """
    return [value.strip() for value in raw_value.split(",") if value.strip()]


def _build_dex_github_config(client_id: str, github_orgs: list[str]) -> str:
    """
    Build the dex.config YAML payload for a GitHub connector.
    """
    org_lines = "\n".join(f"      - name: {org}" for org in github_orgs)
    return (
        "connectors:\n"
        "- type: github\n"
        "  id: github\n"
        "  name: GitHub\n"
        "  config:\n"
        f"    clientID: {client_id}\n"
        "    clientSecret: $dex.github.clientSecret\n"
        "    orgs:\n"
        f"{org_lines}"
    )


def _configure_argocd_github_sso(
    k8s: KubernetesClient,
    cluster_config: ArgoInstallSettings,
) -> None:
    """
    Configure optional GitHub SSO for ArgoCD using Dex.

    Required settings (client id/secret/orgs) are already validated by
    ArgoInstallSettings when SSO is enabled, so this only needs to build
    and apply the Dex connector config.
    """
    if not cluster_config.argocd_github_sso_enabled:
        return

    client_id = cluster_config.argocd_github_oauth_client_id.strip()
    client_secret = cluster_config.argocd_github_oauth_client_secret.strip()
    github_orgs = _split_csv_values(cluster_config.argocd_github_orgs)

    run_command_with_logging(
        logger,
        "configure ArgoCD Dex GitHub connector",
        k8s.patch_config_map,
        name="argocd-cm",
        namespace=ARGOCD_NAMESPACE,
        data={
            "url": f"https://argocd.{cluster_config.cluster_domain}",
            "dex.config": _build_dex_github_config(client_id, github_orgs),
        },
    )

    run_command_with_logging(
        logger,
        "configure ArgoCD Dex GitHub OAuth secret",
        k8s.patch_secret,
        name="argocd-secret",
        namespace=ARGOCD_NAMESPACE,
        string_data={
            "dex.github.clientSecret": client_secret,
        },
    )

    logger.warning("Restart ArgoCD Dex and server pods to apply GitHub SSO changes:")
    logger.warning(
        "  kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-dex-server"
    )
    logger.warning(
        "  kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-server"
    )


def _configure_registry_pull_secrets(
    k8s: KubernetesClient,
    cluster_config: ArgoInstallSettings,
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


def _install_argo_workflows_templates(cluster_config: ArgoInstallSettings) -> None:
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


def install_argo_workflows(cluster_config: ArgoInstallSettings) -> None:
    """
    Install Argo Workflows in the Kubernetes cluster.

    Args:
        cluster_config: Cluster configuration with Argo Workflows settings

    Raises:
        CommandNotFoundError: If required commands are not installed
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


def install_argocd(cluster_config: ArgoInstallSettings) -> None:
    """
    Install ArgoCD in the Kubernetes cluster.

    Args:
        cluster_config: Cluster configuration with ArgoCD settings

    Raises:
        CommandNotFoundError: If required commands are not installed
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
        ARGOCD_NAMESPACE,
    )

    run_command_with_logging(
        logger,
        "install ArgoCD core components",
        k8s.apply_manifest_from_url,
        cluster_config.argocd_install_url,
        ARGOCD_NAMESPACE,
    )

    run_command_with_logging(
        logger,
        "ensure base ArgoCD configmap",
        k8s.apply_manifest_from_url,
        f"{cluster_config.opencraft_manifests_url}/argocd-base-config.yml",
        ARGOCD_NAMESPACE,
    )

    run_command_with_logging(
        logger,
        "ensure ArgoCD server role allows web terminal (pods/exec)",
        k8s.ensure_role_has_pods_exec,
        "argocd-server",
        ARGOCD_NAMESPACE,
    )

    run_command_with_logging(
        logger,
        "configure ArgoCD ingress",
        k8s.apply_manifest_from_url,
        f"{cluster_config.opencraft_manifests_url}/argocd-ingress.yml",
        ARGOCD_NAMESPACE,
        {
            "LAUNCHPAD_CLUSTER_DOMAIN": cluster_config.cluster_domain,
        },
    )

    _configure_argocd_github_sso(k8s, cluster_config)

    run_command_with_logging(
        logger,
        "configure ArgoCD admin password",
        k8s.apply_manifest_from_url,
        f"{cluster_config.opencraft_manifests_url}/argocd-admin-password.yml",
        ARGOCD_NAMESPACE,
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
        [ARGOCD_NAMESPACE],
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

    try:
        settings = ArgoInstallSettings()  # type: ignore[call-arg]
    except ValidationError as e:
        exit_with_error(logger, f"Invalid configuration:\n{e}", exc_info=False)
        return

    setup_kubeconfig()

    try:
        install_both = not settings.argocd_only and not settings.workflows_only

        if install_both or settings.argocd_only:
            logger.info("Installing ArgoCD...")
            install_argocd(settings)

        if install_both or settings.workflows_only:
            logger.info("Installing Argo Workflows...")
            install_argo_workflows(settings)
    except (
        CommandNotFoundError,
        KubernetesError,
        ManifestError,
        PasswordError,
    ) as e:
        exit_with_error(logger, f"Installation failed: {e}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        exit_with_error(logger, f"Unexpected error: {e}", exc_info=False)
