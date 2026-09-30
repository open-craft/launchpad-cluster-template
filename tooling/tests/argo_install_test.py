"""
Unit tests for Argo install helpers.
"""

import argparse
from unittest import mock

import pytest

from launchpad.cli.argo_install import (
    _apply_kustomize,
    _build_argocd_sso_cli_overrides,
    _build_dex_github_config,
    _configure_argocd_github_sso,
    _split_csv_values,
    install_argo_workflows,
    install_argocd,
)
from launchpad.config import ClusterConfig
from launchpad.exceptions import ConfigurationError, KubernetesError


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


def _run_logged_command(_logger, _description, func, *args, **kwargs):
    """
    Invoke the wrapped installer step without CLI logging.
    """

    return func(*args, **kwargs)


class TestInstallArgo:
    """
    Test suite for Argo install orchestration.
    """

    def test_install_argocd_applies_kustomize_overlay(self, monkeypatch):
        """
        Test Argo CD is installed from the kustomize overlay.
        """

        applied = []
        k8s = mock.Mock()

        def apply_kustomize(url, namespace):
            applied.append((url, namespace))

        monkeypatch.setattr(
            "launchpad.cli.argo_install._apply_kustomize", apply_kustomize
        )
        monkeypatch.setattr("launchpad.cli.argo_install.KubernetesClient", lambda: k8s)
        monkeypatch.setattr(
            "launchpad.cli.argo_install.resolve_plaintext_password",
            lambda _password: "generated",
        )
        monkeypatch.setattr(
            "launchpad.cli.argo_install.bcrypt_password", lambda _password: "hashed"
        )
        monkeypatch.setattr(
            "launchpad.cli.argo_install.get_password_mtime", lambda: "mtime"
        )
        monkeypatch.setattr(
            "launchpad.cli.argo_install.run_command_with_logging",
            _run_logged_command,
        )

        config = ClusterConfig(cluster_domain="cluster.domain")
        install_argocd(config)

        assert applied == [(f"{config.opencraft_manifests_url}/argocd", "argocd")]
        k8s.apply_manifest_from_url.assert_any_call(
            f"{config.opencraft_manifests_url}/argocd-base-config.yml",
            "argocd",
        )

    def test_install_argo_workflows_applies_kustomize_overlay(self, monkeypatch):
        """
        Test Argo Workflows is installed from the kustomize overlay.
        """

        applied = []
        k8s = mock.Mock()

        def apply_kustomize(url, namespace):
            applied.append((url, namespace))

        monkeypatch.setattr(
            "launchpad.cli.argo_install._apply_kustomize", apply_kustomize
        )
        monkeypatch.setattr("launchpad.cli.argo_install.KubernetesClient", lambda: k8s)
        monkeypatch.setattr(
            "launchpad.cli.argo_install._install_argo_workflows_templates",
            lambda _config: None,
        )
        monkeypatch.setattr(
            "launchpad.cli.argo_install.run_command_with_logging",
            _run_logged_command,
        )

        config = ClusterConfig(cluster_domain="cluster.domain")
        install_argo_workflows(config)

        assert applied == [(f"{config.opencraft_manifests_url}/argo-workflows", "argo")]

    def test_apply_kustomize_invokes_kubectl(self, monkeypatch):
        """
        Test the overlay is applied with kubectl apply -k.
        """

        completed = mock.Mock(returncode=0, stderr="")
        run = mock.Mock(return_value=completed)
        monkeypatch.setattr("launchpad.cli.argo_install.subprocess.run", run)

        _apply_kustomize("https://example.test/manifests/argocd", "argocd")

        run.assert_called_once_with(
            [
                "kubectl",
                "apply",
                "--server-side",
                "-k",
                "https://example.test/manifests/argocd",
                "-n",
                "argocd",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_apply_kustomize_reports_kubectl_failure(self, monkeypatch):
        """
        Test a failed kubectl apply -k raises KubernetesError.
        """

        completed = mock.Mock(returncode=1, stderr="apply failed")
        run = mock.Mock(return_value=completed)
        monkeypatch.setattr("launchpad.cli.argo_install.subprocess.run", run)

        with pytest.raises(KubernetesError, match="apply failed"):
            _apply_kustomize("https://example.test/manifests/argocd", "argocd")

        run.assert_called_once()
        assert "--force-conflicts" not in run.call_args[0][0]

    def test_apply_kustomize_retries_server_side_conflicts(self, monkeypatch):
        """
        Test a server-side apply conflict retries once with --force-conflicts.
        """

        conflict = mock.Mock(
            returncode=1,
            stderr=(
                "error: Apply failed with 2 conflicts: conflicts with "
                '"kubectl-patch" using apps/v1:\n'
                '- .spec.template.spec.containers[name="argo-server"].args\n'
                '- .spec.template.spec.containers[name="argo-server"]'
                ".readinessProbe.httpGet.scheme"
            ),
        )
        success = mock.Mock(returncode=0, stderr="")
        run = mock.Mock(side_effect=[conflict, success])
        monkeypatch.setattr("launchpad.cli.argo_install.subprocess.run", run)

        _apply_kustomize("https://example.test/manifests/argo-workflows", "argo")

        assert run.call_count == 2
        first_command = run.call_args_list[0][0][0]
        second_command = run.call_args_list[1][0][0]
        assert "--server-side" in first_command
        assert "--force-conflicts" not in first_command
        assert "--force-conflicts" in second_command
