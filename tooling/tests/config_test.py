"""
Unit tests for the configuration module.
"""

import os
from unittest import mock

import pytest
from pydantic import ValidationError

from launchpad.config import (
    ClusterConfig,
    Config,
    InstanceConfig,
    PicassoConfig,
    ProviderConfig,
    StorageConfig,
    get_config,
)


class TestClusterConfig:
    """
    Test suite for ClusterConfig.
    """

    def test_cluster_config_with_required_field(self):
        """
        Test ClusterConfig with required cluster_domain field.
        """

        config = ClusterConfig(cluster_domain="cluster.domain")

        assert config.cluster_domain == "cluster.domain"
        assert config.argocd_version == "stable"
        assert config.argo_workflows_version == "stable"
        assert config.opencraft_manifests_version == "main"
        assert config.argo_admin_password == ""

    def test_cluster_config_custom_values(self):
        """
        Test ClusterConfig with custom values.
        """

        config = ClusterConfig(
            cluster_domain="test.cluster.domain",
            argocd_version="v2.8.0",
            argo_workflows_version="v3.4.0",
            opencraft_manifests_version="develop",
            argo_admin_password="custom_password",
        )

        assert config.cluster_domain == "test.cluster.domain"
        assert config.argocd_version == "v2.8.0"
        assert config.argo_workflows_version == "v3.4.0"
        assert config.opencraft_manifests_version == "develop"
        assert config.argo_admin_password == "custom_password"

    def test_cluster_config_opencraft_manifests_url(self):
        """
        Test the opencraft_manifests_url property.
        """

        config = ClusterConfig(
            cluster_domain="cluster.domain", opencraft_manifests_version="v1.0.0"
        )

        expected_url = "https://raw.githubusercontent.com/open-craft/launchpad-cluster-template/v1.0.0/manifests"
        assert config.opencraft_manifests_url == expected_url

    def test_cluster_config_argocd_install_url(self):
        """
        Test the argocd_install_url property.
        """

        config = ClusterConfig(cluster_domain="cluster.domain", argocd_version="v2.8.0")

        expected_url = "https://raw.githubusercontent.com/argoproj/argo-cd/v2.8.0/manifests/install.yaml"
        assert config.argocd_install_url == expected_url

    def test_cluster_config_argo_workflows_install_url(self):
        """
        Test the argo_workflows_install_url property.
        """

        config = ClusterConfig(
            cluster_domain="cluster.domain", argo_workflows_version="v3.4.0"
        )

        expected_url = "https://raw.githubusercontent.com/argoproj/argo-workflows/v3.4.0/manifests/install.yaml"
        assert config.argo_workflows_install_url == expected_url

    def test_cluster_config_frozen(self):
        """
        Test that ClusterConfig is frozen (immutable).
        """

        config = ClusterConfig(cluster_domain="cluster.domain")

        with pytest.raises(ValidationError, match="frozen"):
            config.cluster_domain = "new.cluster.domain"

    def test_cluster_config_extra_forbidden(self):
        """
        Test that extra fields are forbidden.
        """

        with pytest.raises(ValidationError, match="extra"):
            ClusterConfig(cluster_domain="cluster.domain", extra_field="value")

    def test_cluster_config_env_prefix(self):
        """
        Test that environment variables with LAUNCHPAD_ prefix are loaded.
        """

        with mock.patch.dict(
            os.environ,
            {
                "LAUNCHPAD_CLUSTER_DOMAIN": "env.cluster.domain",
                "LAUNCHPAD_ARGOCD_VERSION": "v2.9.0",
            },
        ):
            config = ClusterConfig()

            assert config.cluster_domain == "env.cluster.domain"
            assert config.argocd_version == "v2.9.0"


class TestInstanceConfig:
    """
    Test suite for InstanceConfig.
    """

    def test_instance_config_creation(self):
        """
        Test basic InstanceConfig creation.
        """

        config = InstanceConfig()

        assert config is not None

    def test_instance_config_frozen(self):
        """
        Test that InstanceConfig is frozen.
        """

        config = InstanceConfig()

        assert config.model_config["frozen"] is True


class TestProviderConfig:
    """
    Test suite for ProviderConfig.
    """

    def test_provider_config_creation(self):
        """
        Test basic ProviderConfig creation.
        """

        config = ProviderConfig()

        assert config is not None

    def test_provider_config_frozen(self):
        """
        Test that ProviderConfig is frozen.
        """

        config = ProviderConfig()

        assert config.model_config["frozen"] is True


class TestStorageConfig:
    """
    Test suite for StorageConfig.
    """

    def test_storage_config_creation(self):
        """
        Test basic StorageConfig creation.
        """

        config = StorageConfig()

        assert config is not None

    def test_storage_config_frozen(self):
        """
        Test that StorageConfig is frozen.
        """

        config = StorageConfig()

        assert config.model_config["frozen"] is True


class TestPicassoConfig:
    """
    Test suite for PicassoConfig.
    """

    def test_picasso_config_creation(self):
        """
        Test basic PicassoConfig creation.
        """

        config = PicassoConfig()

        assert config is not None

    def test_picasso_config_frozen(self):
        """
        Test that PicassoConfig is frozen.
        """

        config = PicassoConfig()

        assert config.model_config["frozen"] is True


class TestConfig:
    """
    Test suite for main Config class.
    """

    @mock.patch.dict(os.environ, {"LAUNCHPAD_CLUSTER_DOMAIN": "test.cluster.domain"})
    def test_config_creation_with_env(self):
        """
        Test Config creation with environment variables.
        """

        config = Config()

        assert config.log_level == "INFO"
        assert "launchpad.log" in config.log_file
        assert config.cluster.cluster_domain == "test.cluster.domain"

    @mock.patch.dict(os.environ, {"LAUNCHPAD_CLUSTER_DOMAIN": "test.cluster.domain"})
    def test_config_default_values(self):
        """
        Test Config default values.
        """

        config = Config()

        assert config.log_level == "INFO"
        assert "launchpad.log" in config.log_file
        assert config.log_format == "%(asctime)s - %(levelname)s - %(message)s"

    @mock.patch.dict(
        os.environ,
        {
            "LAUNCHPAD_LOG_LEVEL": "DEBUG",
            "LAUNCHPAD_LOG_FILE": "custom.log",
            "LAUNCHPAD_CLUSTER_DOMAIN": "test.cluster.domain",
        },
    )
    def test_config_custom_log_values(self):
        """
        Test Config with custom log values from environment.
        """

        config = Config()

        assert config.log_level == "DEBUG"
        assert config.log_file == "custom.log"

    @mock.patch.dict(os.environ, {"LAUNCHPAD_CLUSTER_DOMAIN": "test.cluster.domain"})
    def test_config_nested_configs(self):
        """
        Test that Config contains all nested configuration layers.
        """

        config = Config()

        assert isinstance(config.cluster, ClusterConfig)
        assert isinstance(config.instance, InstanceConfig)
        assert isinstance(config.provider, ProviderConfig)
        assert isinstance(config.storage, StorageConfig)
        assert isinstance(config.picasso, PicassoConfig)

    @mock.patch.dict(os.environ, {"LAUNCHPAD_CLUSTER_DOMAIN": "test.cluster.domain"})
    def test_config_frozen(self):
        """
        Test that Config is frozen.
        """

        config = Config()

        with pytest.raises(ValidationError, match="frozen"):
            config.log_level = "ERROR"


class TestGetConfig:
    """
    Test suite for get_config function.
    """

    @mock.patch.dict(os.environ, {"LAUNCHPAD_CLUSTER_DOMAIN": "test.cluster.domain"})
    def test_get_config_returns_config(self):
        """
        Test that get_config returns a Config instance.
        """

        import launchpad.config

        launchpad.config._CONFIG_INSTANCE = None

        config = get_config()

        assert isinstance(config, Config)

    @mock.patch.dict(os.environ, {"LAUNCHPAD_CLUSTER_DOMAIN": "test.cluster.domain"})
    def test_get_config_singleton(self):
        """
        Test that get_config returns the same instance (singleton pattern).
        """

        import launchpad.config

        launchpad.config._CONFIG_INSTANCE = None

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    @mock.patch.dict(os.environ, {"LAUNCHPAD_CLUSTER_DOMAIN": "test.cluster.domain"})
    def test_get_config_lazy_initialization(self):
        """
        Test that get_config uses lazy initialization.
        """

        import launchpad.config

        launchpad.config._CONFIG_INSTANCE = None

        assert launchpad.config._CONFIG_INSTANCE is None
        config = get_config()
        assert launchpad.config._CONFIG_INSTANCE is not None
        assert config is launchpad.config._CONFIG_INSTANCE
