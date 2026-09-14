"""
Unit tests for Argo install helpers.
"""

from unittest import mock

import pytest
from pydantic import ValidationError

from launchpad.cli.argo_install import (
    ArgoInstallSettings,
    _build_dex_github_config,
    _configure_argocd_github_sso,
    _split_csv_values,
)


def _settings(**overrides) -> ArgoInstallSettings:
    """
    Build ArgoInstallSettings from explicit kwargs only, without parsing
    sys.argv or reading LAUNCHPAD_* environment variables from the test
    process.
    """
    return ArgoInstallSettings(_cli_parse_args=False, **overrides)


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


class TestArgoInstallSettingsGithubSsoValidation:
    """
    Test suite for ArgoInstallSettings' eager GitHub SSO validation.

    These replace the old runtime check inside _configure_argocd_github_sso:
    invalid SSO configuration must now fail as soon as ArgoInstallSettings is
    constructed, before any Kubernetes resource is touched.
    """

    def test_construction_succeeds_when_sso_disabled(self):
        """
        Test no validation error occurs when SSO is disabled, regardless of
        other GitHub fields being empty.
        """

        settings = _settings(cluster_domain="cluster.domain")

        assert settings.argocd_github_sso_enabled is False

    def test_construction_fails_when_sso_enabled_without_required_fields(self):
        """
        Test constructing ArgoInstallSettings raises when SSO is enabled but
        client id/orgs are missing.
        """

        with pytest.raises(ValidationError, match="GitHub SSO is enabled"):
            _settings(
                cluster_domain="cluster.domain",
                argocd_github_sso_enabled=True,
                argocd_github_oauth_client_secret="secret",
            )

    def test_construction_succeeds_when_sso_enabled_with_all_required_fields(self):
        """
        Test constructing ArgoInstallSettings succeeds when SSO is enabled and
        all required GitHub fields are provided.
        """

        settings = _settings(
            cluster_domain="cluster.domain",
            argocd_github_sso_enabled=True,
            argocd_github_oauth_client_id="client-id",
            argocd_github_oauth_client_secret="client-secret",
            argocd_github_orgs="open-craft,example-org",
        )

        assert settings.argocd_github_sso_enabled is True


class TestConfigureArgocdGithubSso:
    """
    Test suite for _configure_argocd_github_sso.
    """

    def test_configure_argocd_github_sso_skips_when_disabled(self):
        """
        Test SSO configuration is skipped when explicitly disabled.
        """

        k8s = mock.Mock()
        settings = _settings(cluster_domain="cluster.domain")

        _configure_argocd_github_sso(k8s, settings)

        k8s.patch_config_map.assert_not_called()
        k8s.patch_secret.assert_not_called()

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
        settings = _settings(
            cluster_domain="cluster.domain",
            argocd_github_sso_enabled=True,
            argocd_github_oauth_client_id="client-id",
            argocd_github_oauth_client_secret="client-secret",
            argocd_github_orgs="open-craft,example-org",
        )

        _configure_argocd_github_sso(k8s, settings)

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
