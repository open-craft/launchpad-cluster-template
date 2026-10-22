"""
Configuration defined for Launchpad split across configuration layers.

Individual settings fields are declared once each, as single-field mixins
(``*Field`` classes below), and composed into the settings classes that
actually use them. This lets a command-specific settings class (e.g.
``ArgoInstallSettings`` in ``launchpad.cli.argo_install``) reuse exactly the
fields it needs from ``ClusterConfig`` without inheriting fields it doesn't
use, and without redeclaring shared fields.
"""

import json
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LaunchpadBaseSettings(BaseSettings):
    """
    Base settings for Launchpad.
    """

    model_config = SettingsConfigDict(
        env_prefix="LAUNCHPAD_",
        extra="forbid",
        frozen=True,
    )


def _load_cluster_domain_from_context() -> str:
    """
    Load cluster domain from context.json file in the current directory.

    Returns:
        Cluster domain from context.json, or empty string if not found
    """
    try:
        context_file = Path.cwd() / "context.json"
        if context_file.exists():
            with open(context_file, "r", encoding="utf-8") as f:
                context = json.load(f)
                return context.get("cluster_domain", "")
    except (json.JSONDecodeError, KeyError, OSError):
        pass
    return ""


# --- Single-field mixins ----------------------------------------------------
#
# Each mixin declares exactly one field. Settings classes compose only the
# mixins for the fields they actually use (see ClusterConfig and
# ArgoInstallSettings below).


class ClusterDomainField(BaseModel):
    """Cluster domain field."""

    cluster_domain: str = Field(
        default_factory=_load_cluster_domain_from_context,
        description="Cluster domain (e.g., cluster.domain)",
    )


class EnvironmentField(BaseModel):
    """Environment field."""

    environment: str = Field(
        default="production", description="Environment (production, staging, etc.)"
    )


class ArgocdVersionField(BaseModel):
    """ArgoCD version field."""

    argocd_version: str = Field(
        default="stable", description="ArgoCD version to install"
    )


class ArgoWorkflowsVersionField(BaseModel):
    """Argo Workflows version field."""

    argo_workflows_version: str = Field(
        default="stable", description="Argo Workflows version to install"
    )


class ArgocdInstallUrlMixin(ArgocdVersionField):
    """Adds the derived ArgoCD install manifest URL to ArgocdVersionField."""

    @property
    def argocd_install_url(self) -> str:
        """
        Get the ArgoCD installation URL.
        """

        return f"https://raw.githubusercontent.com/argoproj/argo-cd/{self.argocd_version}/manifests/install.yaml"


class ArgoWorkflowsInstallUrlMixin(ArgoWorkflowsVersionField):
    """Adds the derived Argo Workflows install manifest URL to ArgoWorkflowsVersionField."""

    @property
    def argo_workflows_install_url(self) -> str:
        """
        Get the Argo Workflows installation URL.
        """

        return f"https://raw.githubusercontent.com/argoproj/argo-workflows/{self.argo_workflows_version}/manifests/install.yaml"


class OpencraftManifestsVersionField(BaseModel):
    """OpenCraft manifests version field."""

    opencraft_manifests_version: str = Field(
        default="main", description="OpenCraft manifests version"
    )


class OpencraftManifestsUrlMixin(OpencraftManifestsVersionField):
    """Adds the derived OpenCraft manifests URL to OpencraftManifestsVersionField."""

    @property
    def opencraft_manifests_url(self) -> str:
        """
        Get the OpenCraft manifests URL.
        """

        return f"https://raw.githubusercontent.com/open-craft/launchpad-cluster-template/{self.opencraft_manifests_version}/manifests"


class InstancesDirectoryField(BaseModel):
    """Instances directory field."""

    instances_directory: str = Field(
        default="instances", description="Directory where instances are stored"
    )


class DockerRegistryField(BaseModel):
    """Docker registry hostname field."""

    docker_registry: str = Field(
        default="ghcr.io",
        description="Docker registry hostname (e.g., ghcr.io)",
    )


class DockerRegistryCredentialsField(BaseModel):
    """Docker registry credentials field."""

    docker_registry_credentials: str = Field(
        default="",
        description=(
            "Base64-encoded '<username>:<token>' auth for Docker registry "
            "(used to create imagePullSecrets)"
        ),
    )


class ArgoAdminPasswordField(BaseModel):
    """Argo admin password field."""

    argo_admin_password: str = Field(
        default="", description="Argo admin password (plaintext)"
    )


class ArgocdGithubSsoEnabledField(BaseModel):
    """ArgoCD GitHub SSO enabled field."""

    argocd_github_sso_enabled: bool = Field(
        default=False, description="Enable ArgoCD GitHub SSO via Dex"
    )


class ArgocdGithubOauthClientIdField(BaseModel):
    """ArgoCD GitHub OAuth client ID field."""

    argocd_github_oauth_client_id: str = Field(
        default="", description="GitHub OAuth app client ID for ArgoCD Dex connector"
    )


class ArgocdGithubOauthClientSecretField(BaseModel):
    """ArgoCD GitHub OAuth client secret field."""

    argocd_github_oauth_client_secret: str = Field(
        default="",
        description="GitHub OAuth app client secret for ArgoCD Dex connector",
    )


class ArgocdGithubOrgsField(BaseModel):
    """ArgoCD GitHub allowed orgs field."""

    argocd_github_orgs: str = Field(
        default="",
        description="Comma-separated GitHub org slugs allowed to sign in via Dex",
    )


class ClusterConfig(
    LaunchpadBaseSettings,
    ClusterDomainField,
    EnvironmentField,
    ArgocdInstallUrlMixin,
    ArgoWorkflowsInstallUrlMixin,
    OpencraftManifestsUrlMixin,
    InstancesDirectoryField,
    DockerRegistryField,
    DockerRegistryCredentialsField,
    ArgoAdminPasswordField,
    ArgocdGithubSsoEnabledField,
    ArgocdGithubOauthClientIdField,
    ArgocdGithubOauthClientSecretField,
    ArgocdGithubOrgsField,
):
    """
    Cluster configuration.

    Composed from single-field mixins declared above so that command-specific
    settings classes (e.g. ArgoInstallSettings) can reuse individual fields
    without inheriting this whole class.
    """


class InstanceConfig(LaunchpadBaseSettings):
    """
    Instance configuration.
    """


class ProviderConfig(LaunchpadBaseSettings):
    """
    Provider configuration.
    """


class StorageConfig(LaunchpadBaseSettings):
    """
    Storage configuration.
    """


class PicassoConfig(LaunchpadBaseSettings):
    """
    Picasso configuration.
    """


class Config(LaunchpadBaseSettings):
    """
    Main configuration class.
    """

    # Global configuration
    log_level: str = Field(default="INFO", description="Log level")
    log_file: str = Field(
        # pylint: disable=unnecessary-lambda
        default_factory=lambda: str(Path(tempfile.gettempdir()) / "launchpad.log"),
        description="Log file (defaults to temp directory)",
    )
    log_format: str = Field(
        default="%(asctime)s - %(levelname)s - %(message)s",
        description="Log format",
    )

    # Configuration layers
    cluster: ClusterConfig = Field(
        default_factory=ClusterConfig, description="Cluster configuration"
    )
    instance: InstanceConfig = Field(
        default_factory=InstanceConfig, description="Instance configuration"
    )
    provider: ProviderConfig = Field(
        default_factory=ProviderConfig, description="Provider configuration"
    )
    storage: StorageConfig = Field(
        default_factory=StorageConfig, description="Storage configuration"
    )
    picasso: PicassoConfig = Field(
        default_factory=PicassoConfig, description="Picasso configuration"
    )


_CONFIG_INSTANCE = None


def get_config() -> Config:
    """
    Get the global configuration instance (lazy initialization).

    Returns:
        Config: The global configuration
    """

    global _CONFIG_INSTANCE  # pylint: disable=global-statement

    if _CONFIG_INSTANCE is None:
        _CONFIG_INSTANCE = Config()

    return _CONFIG_INSTANCE
