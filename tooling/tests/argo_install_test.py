"""
Unit tests for Argo install helpers.
"""

import argparse
from unittest import mock

import pytest

from launchpad.cli.argo_install import (
    _build_argocd_sso_cli_overrides,
    _build_dex_github_config,
    _configure_argocd_github_sso,
    _split_csv_values,
)
from launchpad.config import ClusterConfig
from launchpad.exceptions import ConfigurationError


class TestSplitCsvValues:
    """
    Test suite for _split_csv_values.
    """

    def test_split_csv_values_trims_and_removes_empty_values(self):
        """
        Test comma-separated values are normalized to a clean list.
        """

        result = _split_csv_values(" open-craft , , example-org,  ")

        assert result == ["open-craft", "example-org"]


class TestBuildDexGithubConfig:
    """
    Test suite for _build_dex_github_config.
    """

    def test_build_dex_github_config_contains_expected_connector(self):
        """
        Test generated Dex connector config includes key GitHub settings.
        """

        result = _build_dex_github_config("client-id", ["open-craft", "example-org"])

        assert "type: github" in result
        assert "clientID: client-id" in result
        assert "clientSecret: $dex.github.clientSecret" in result
        assert "      - name: open-craft" in result
        assert "      - name: example-org" in result


class TestBuildArgocdSsoCliOverrides:
    """
    Test suite for _build_argocd_sso_cli_overrides.
    """

    def test_build_argocd_sso_cli_overrides_returns_empty_dict(self):
        """
        Test no overrides are produced when CLI args are not provided.
        """

        args = argparse.Namespace(
            argocd_github_sso_enabled=None,
            argocd_github_oauth_client_id=None,
            argocd_github_oauth_client_secret=None,
            argocd_github_orgs=None,
        )

        assert _build_argocd_sso_cli_overrides(args) == {}

    def test_build_argocd_sso_cli_overrides_returns_provided_values(self):
        """
        Test only explicitly provided CLI values are included as overrides.
        """

        args = argparse.Namespace(
            argocd_github_sso_enabled=True,
            argocd_github_oauth_client_id="client-id",
            argocd_github_oauth_client_secret="client-secret",
            argocd_github_orgs="open-craft,example-org",
        )

        assert _build_argocd_sso_cli_overrides(args) == {
            "argocd_github_sso_enabled": True,
            "argocd_github_oauth_client_id": "client-id",
            "argocd_github_oauth_client_secret": "client-secret",
            "argocd_github_orgs": "open-craft,example-org",
        }


class TestConfigureArgocdGithubSso:
    """
    Test suite for _configure_argocd_github_sso.
    """

    def test_configure_argocd_github_sso_skips_when_disabled(self):
        """
        Test SSO configuration is skipped when explicitly disabled.
        """

        k8s = mock.Mock()
        cluster_config = ClusterConfig(cluster_domain="cluster.domain")

        _configure_argocd_github_sso(k8s, cluster_config)

        k8s.patch_config_map.assert_not_called()
        k8s.patch_secret.assert_not_called()

    def test_configure_argocd_github_sso_validates_required_settings(self):
        """
        Test SSO configuration fails when required values are missing.
        """

        k8s = mock.Mock()
        cluster_config = ClusterConfig(
            cluster_domain="cluster.domain",
            argocd_github_sso_enabled=True,
            argocd_github_oauth_client_id="",
            argocd_github_oauth_client_secret="secret",
            argocd_github_orgs="",
        )

        with pytest.raises(
            ConfigurationError,
            match=(
                "LAUNCHPAD_ARGOCD_GITHUB_OAUTH_CLIENT_ID, "
                "LAUNCHPAD_ARGOCD_GITHUB_ORGS"
            ),
        ):
            _configure_argocd_github_sso(k8s, cluster_config)

    def test_configure_argocd_github_sso_patches_configmap_and_secret(
        self, monkeypatch
    ):
        """
        Test SSO setup patches both argocd-cm and argocd-secret.
        """

        def _run_with_logging(_logger, _description, func, *args, **kwargs):
            return func(*args, **kwargs)

        monkeypatch.setattr(
            "launchpad.cli.argo_install.run_command_with_logging",
            _run_with_logging,
        )

        k8s = mock.Mock()
        cluster_config = ClusterConfig(
            cluster_domain="cluster.domain",
            argocd_github_sso_enabled=True,
            argocd_github_oauth_client_id="client-id",
            argocd_github_oauth_client_secret="client-secret",
            argocd_github_orgs="open-craft,example-org",
        )

        _configure_argocd_github_sso(k8s, cluster_config)

        k8s.patch_config_map.assert_called_once()
        patch_cm_kwargs = k8s.patch_config_map.call_args.kwargs
        assert patch_cm_kwargs["name"] == "argocd-cm"
        assert patch_cm_kwargs["namespace"] == "argocd"
        assert patch_cm_kwargs["data"]["url"] == "https://argocd.cluster.domain"
        assert patch_cm_kwargs["data"]["dex.config"] == _build_dex_github_config(
            "client-id", ["open-craft", "example-org"]
        )

        k8s.patch_secret.assert_called_once_with(
            name="argocd-secret",
            namespace="argocd",
            string_data={"dex.github.clientSecret": "client-secret"},
        )
