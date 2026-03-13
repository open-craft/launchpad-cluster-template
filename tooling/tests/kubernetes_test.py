"""
Unit tests for the Kubernetes utility functions.
"""

import subprocess
from unittest import mock

import pytest
import requests
from kubernetes import client

from launchpad.exceptions import KubernetesError, ManifestError
from launchpad.kubernetes import KubernetesClient, build_dockerconfigjson


class TestKubernetesClient:
    """
    Test suite for KubernetesClient.
    """

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_init(
        self,
        _mock_get_logger,
        mock_load_config,
        mock_api_client,
        mock_apps_v1,
        mock_core_v1,
        mock_rbac_v1,
    ):
        """
        Test that KubernetesClient initializes properly.
        """

        k8s_client = KubernetesClient()

        mock_load_config.assert_called_once()
        mock_api_client.assert_called_once()
        mock_core_v1.assert_called_once()
        mock_apps_v1.assert_called_once()
        mock_rbac_v1.assert_called_once()

        assert k8s_client is not None
        assert k8s_client._api_client is not None
        assert k8s_client._core_v1 is not None
        assert k8s_client._apps_v1 is not None
        assert k8s_client._rbac_v1 is not None

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    @mock.patch("launchpad.kubernetes.requests.get")
    def test_get_manifest_from_url_success(
        self,
        mock_get,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        _mock_rbac_v1,
    ):
        """
        Test successful retrieval of manifest from URL.
        """

        url = "https://cluster.domain/manifest.yaml"
        manifest_content = "apiVersion: v1\nkind: ConfigMap"
        mock_response = mock.Mock()
        mock_response.text = manifest_content
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response

        k8s_client = KubernetesClient()
        result = k8s_client._KubernetesClient__get_manifest_from_url(url)

        mock_get.assert_called_once_with(url, timeout=30)
        mock_response.raise_for_status.assert_called_once()
        assert result == manifest_content

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    @mock.patch("launchpad.kubernetes.requests.get")
    def test_get_manifest_from_url_http_error(
        self,
        mock_get,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        _mock_rbac_v1,
    ):
        """
        Test handling of HTTP errors when retrieving manifest from URL.
        """

        url = "https://cluster.domain/manifest.yaml"
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

        k8s_client = KubernetesClient()

        with pytest.raises(ManifestError, match="Failed to fetch manifest"):
            k8s_client._KubernetesClient__get_manifest_from_url(url)

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_render_manifest_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        _mock_rbac_v1,
    ):
        """
        Test successful manifest rendering with Jinja2.
        """

        manifest = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: {{ NAME }}"
        variables = {"NAME": "test-config"}

        k8s_client = KubernetesClient()
        result = k8s_client.render_manifest(manifest, variables)

        assert "test-config" in result
        assert "{{ NAME }}" not in result

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_render_manifest_undefined_variables(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        _mock_rbac_v1,
    ):
        """
        Test that undefined variables are rendered as empty strings by Jinja2.
        """

        manifest = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: {{ UNDEFINED }}"
        variables = {}

        k8s_client = KubernetesClient()
        result = k8s_client.render_manifest(manifest, variables)

        assert "{{ UNDEFINED }}" not in result
        assert "name: " in result

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    @mock.patch("launchpad.kubernetes.subprocess.run")
    @mock.patch("launchpad.kubernetes.yaml.safe_load_all")
    def test_apply_manifest_success(
        self,
        mock_yaml_load,
        mock_subprocess_run,
        _mock_get_logger,
        _mock_load_config,
        mock_api_client_class,
        _mock_apps_v1_class,
        _mock_core_v1,
        _mock_rbac_v1,
    ):
        """
        Test successful application of a manifest.
        """

        mock_api_client_instance = mock.Mock()
        mock_api_client_class.return_value = mock_api_client_instance

        manifest = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test-config"
        doc = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "test-config"},
        }
        mock_yaml_load.return_value = [doc]

        # Mock successful kubectl apply
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "configmap/test-config created"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        k8s_client = KubernetesClient()
        k8s_client.apply_manifest(manifest, namespace="test-ns")

        # Verify kubectl apply was called (with --server-side)
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args
        assert call_args[0][0] == [
            "kubectl",
            "apply",
            "--server-side",
            "-f",
            "-",
            "-n",
            "test-ns",
        ]

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    @mock.patch("launchpad.kubernetes.subprocess.run")
    @mock.patch("launchpad.kubernetes.yaml.safe_load_all")
    def test_apply_manifest_with_variables(
        self,
        mock_yaml_load,
        mock_subprocess_run,
        _mock_get_logger,
        _mock_load_config,
        mock_api_client_class,
        _mock_apps_v1_class,
        _mock_core_v1,
        _mock_rbac_v1,
    ):
        """
        Test application of manifest with Jinja2 variables.
        """

        mock_api_client_instance = mock.Mock()
        mock_api_client_class.return_value = mock_api_client_instance

        manifest = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: {{ NAME }}"
        variables = {"NAME": "test-config"}
        doc = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "test-config"},
        }
        mock_yaml_load.return_value = [doc]

        # Mock successful kubectl apply
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "configmap/test-config configured"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        k8s_client = KubernetesClient()
        k8s_client.apply_manifest(manifest, namespace="test-ns", variables=variables)

        mock_subprocess_run.assert_called_once()

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    @mock.patch("launchpad.kubernetes.subprocess.run")
    @mock.patch("launchpad.kubernetes.yaml.safe_load_all")
    def test_apply_manifest_multiple_documents(
        self,
        mock_yaml_load,
        mock_subprocess_run,
        _mock_get_logger,
        _mock_load_config,
        mock_api_client_class,
        _mock_apps_v1_class,
        _mock_core_v1,
        _mock_rbac_v1,
    ):
        """
        Test application of manifest with multiple documents.
        """

        mock_api_client_instance = mock.Mock()
        mock_api_client_class.return_value = mock_api_client_instance

        manifest = "---\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cm1\n---\napiVersion: v1\nkind: Secret\nmetadata:\n  name: s1"
        doc1 = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "cm1"}}
        doc2 = {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": "s1"}}
        mock_yaml_load.return_value = [doc1, doc2]

        # Mock successful kubectl apply
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "created"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        k8s_client = KubernetesClient()
        k8s_client.apply_manifest(manifest, namespace="test-ns")

        assert mock_subprocess_run.call_count == 2

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    @mock.patch("launchpad.kubernetes.subprocess.run")
    @mock.patch("launchpad.kubernetes.yaml.safe_load_all")
    def test_apply_manifest_failure(
        self,
        mock_yaml_load,
        mock_subprocess_run,
        _mock_get_logger,
        _mock_load_config,
        mock_api_client_class,
        _mock_apps_v1_class,
        _mock_core_v1,
        _mock_rbac_v1,
    ):
        """
        Test handling of failure when applying manifest.
        """

        mock_api_client_instance = mock.Mock()
        mock_api_client_class.return_value = mock_api_client_instance

        manifest = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test-cm"
        doc = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "test-cm"}}
        mock_yaml_load.return_value = [doc]

        # Mock failed kubectl apply
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            1, ["kubectl", "apply"], stderr="Apply failed"
        )

        k8s_client = KubernetesClient()

        with pytest.raises(KubernetesError, match="Failed to apply"):
            k8s_client.apply_manifest(manifest, namespace="test-ns")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    @mock.patch("launchpad.kubernetes.requests.get")
    @mock.patch("launchpad.kubernetes.subprocess.run")
    @mock.patch("launchpad.kubernetes.yaml.safe_load_all")
    def test_apply_manifest_from_url_success(
        self,
        mock_yaml_load,
        mock_subprocess_run,
        mock_get,
        _mock_get_logger,
        _mock_load_config,
        mock_api_client_class,
        _mock_apps_v1_class,
        _mock_core_v1,
        _mock_rbac_v1,
    ):
        """
        Test successful application of manifest from URL.
        """

        mock_api_client_instance = mock.Mock()
        mock_api_client_class.return_value = mock_api_client_instance

        url = "https://cluster.domain/manifest.yaml"
        manifest_content = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test-cm"
        mock_response = mock.Mock()
        mock_response.text = manifest_content
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response

        doc = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "test-cm"}}
        mock_yaml_load.return_value = [doc]

        # Mock successful kubectl apply
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "configmap/test-cm created"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        k8s_client = KubernetesClient()
        k8s_client.apply_manifest_from_url(url, namespace="test-ns")

        mock_get.assert_called_once_with(url, timeout=30)
        mock_subprocess_run.assert_called_once()

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    @mock.patch("launchpad.kubernetes.requests.get")
    @mock.patch("launchpad.kubernetes.subprocess.run")
    @mock.patch("launchpad.kubernetes.yaml.safe_load_all")
    def test_apply_manifest_from_url_with_variables(
        self,
        mock_yaml_load,
        mock_subprocess_run,
        mock_get,
        _mock_get_logger,
        _mock_load_config,
        mock_api_client_class,
        _mock_apps_v1_class,
        _mock_core_v1,
        _mock_rbac_v1,
    ):
        """
        Test application of manifest from URL with Jinja2 variables.
        """

        mock_api_client_instance = mock.Mock()
        mock_api_client_class.return_value = mock_api_client_instance

        url = "https://cluster.domain/manifest.yaml"
        manifest_content = (
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: {{ NAME }}"
        )
        mock_response = mock.Mock()
        mock_response.text = manifest_content
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response

        variables = {"NAME": "test-config"}
        doc = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "test-config"},
        }
        mock_yaml_load.return_value = [doc]

        # Mock successful kubectl apply
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "configmap/test-config created"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        k8s_client = KubernetesClient()
        k8s_client.apply_manifest_from_url(
            url, namespace="test-ns", variables=variables
        )

        mock_get.assert_called_once_with(url, timeout=30)
        mock_subprocess_run.assert_called_once()

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    @mock.patch("launchpad.kubernetes.requests.get")
    def test_apply_manifest_from_url_fetch_failure(
        self,
        mock_get,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        _mock_rbac_v1,
    ):
        """
        Test handling of fetch failure when applying manifest from URL.
        """

        url = "https://cluster.domain/manifest.yaml"
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        k8s_client = KubernetesClient()

        with pytest.raises(ManifestError, match="Failed to fetch manifest"):
            k8s_client.apply_manifest_from_url(url, namespace="test-ns")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_create_namespace_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test successful namespace creation.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        k8s_client = KubernetesClient()
        k8s_client.create_namespace("test-namespace")

        mock_core_v1_instance.create_namespace.assert_called_once()

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_create_namespace_already_exists(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test namespace creation when namespace already exists (409).
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        api_exception = client.exceptions.ApiException(status=409, reason="Conflict")
        mock_core_v1_instance.create_namespace.side_effect = api_exception

        k8s_client = KubernetesClient()
        k8s_client.create_namespace("test-namespace")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_create_namespace_api_error(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test namespace creation with API error (non-409).
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        api_exception = client.exceptions.ApiException(status=403, reason="Forbidden")
        mock_core_v1_instance.create_namespace.side_effect = api_exception

        k8s_client = KubernetesClient()

        with pytest.raises(KubernetesError, match="Failed to create namespace"):
            k8s_client.create_namespace("test-namespace")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_create_namespace_generic_error(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test namespace creation with generic error.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        mock_core_v1_instance.create_namespace.side_effect = Exception(
            "Unexpected error"
        )

        k8s_client = KubernetesClient()

        with pytest.raises(KubernetesError, match="Failed to create namespace"):
            k8s_client.create_namespace("test-namespace")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_patch_secret_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test successful secret patching.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        k8s_client = KubernetesClient()
        k8s_client.patch_secret(
            name="test-secret",
            namespace="test-ns",
            data={"key": "dmFsdWU="},
        )

        mock_core_v1_instance.patch_namespaced_secret.assert_called_once_with(
            name="test-secret",
            namespace="test-ns",
            body={"data": {"key": "dmFsdWU="}},
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_patch_secret_with_string_data(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test secret patching with stringData.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        k8s_client = KubernetesClient()
        k8s_client.patch_secret(
            name="test-secret",
            namespace="test-ns",
            string_data={"key": "value"},
        )

        mock_core_v1_instance.patch_namespaced_secret.assert_called_once_with(
            name="test-secret",
            namespace="test-ns",
            body={"stringData": {"key": "value"}},
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_patch_secret_failure(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test secret patching failure.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        mock_core_v1_instance.patch_namespaced_secret.side_effect = Exception(
            "Patch failed"
        )

        k8s_client = KubernetesClient()

        with pytest.raises(KubernetesError, match="Failed to patch secret"):
            k8s_client.patch_secret(
                name="test-secret", namespace="test-ns", data={"key": "value"}
            )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_patch_config_map_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test successful config map patching.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        k8s_client = KubernetesClient()
        k8s_client.patch_config_map(
            name="test-cm",
            namespace="test-ns",
            data={"key": "value"},
        )

        mock_core_v1_instance.patch_namespaced_config_map.assert_called_once_with(
            name="test-cm",
            namespace="test-ns",
            body={"data": {"key": "value"}},
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_patch_config_map_failure(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test config map patching failure.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        mock_core_v1_instance.patch_namespaced_config_map.side_effect = Exception(
            "Patch failed"
        )

        k8s_client = KubernetesClient()

        with pytest.raises(KubernetesError, match="Failed to patch config map"):
            k8s_client.patch_config_map(
                name="test-cm", namespace="test-ns", data={"key": "value"}
            )

    def test_build_dockerconfigjson_success(self):
        dockerconfigjson = build_dockerconfigjson(
            registry="ghcr.io", auth="Zm9vOmJhcg=="
        )
        assert dockerconfigjson == '{"auths":{"ghcr.io":{"auth":"Zm9vOmJhcg=="}}}'

    def test_build_dockerconfigjson_missing_registry_raises(self):
        with pytest.raises(KubernetesError, match="Docker registry is empty"):
            build_dockerconfigjson(registry="", auth="Zm9vOmJhcg==")

    def test_build_dockerconfigjson_missing_auth_raises(self):
        with pytest.raises(
            KubernetesError, match="Docker registry credentials are empty"
        ):
            build_dockerconfigjson(registry="ghcr.io", auth="")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_ensure_service_account_image_pull_secret_patches_when_missing(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        sa = mock.Mock()
        sa.image_pull_secrets = []
        mock_core_v1_instance.read_namespaced_service_account.return_value = sa

        k8s_client = KubernetesClient()
        updated = k8s_client.ensure_service_account_image_pull_secret(
            namespace="test-ns",
            service_account_name="default",
            secret_name="launchpad-docker-registry",
        )

        assert updated is True
        mock_core_v1_instance.patch_namespaced_service_account.assert_called_once_with(
            name="default",
            namespace="test-ns",
            body={"imagePullSecrets": [{"name": "launchpad-docker-registry"}]},
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_ensure_service_account_image_pull_secret_noop_if_already_present(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        sa = mock.Mock()
        sa.image_pull_secrets = [{"name": "launchpad-docker-registry"}]
        mock_core_v1_instance.read_namespaced_service_account.return_value = sa

        k8s_client = KubernetesClient()
        updated = k8s_client.ensure_service_account_image_pull_secret(
            namespace="test-ns",
            service_account_name="default",
            secret_name="launchpad-docker-registry",
        )

        assert updated is False
        mock_core_v1_instance.patch_namespaced_service_account.assert_not_called()

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_ensure_service_account_image_pull_secret_returns_false_if_sa_missing(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        mock_core_v1_instance.read_namespaced_service_account.side_effect = (
            client.exceptions.ApiException(status=404, reason="Not Found")
        )

        k8s_client = KubernetesClient()
        updated = k8s_client.ensure_service_account_image_pull_secret(
            namespace="test-ns",
            service_account_name="missing",
            secret_name="launchpad-docker-registry",
        )

        assert updated is False
        mock_core_v1_instance.patch_namespaced_service_account.assert_not_called()

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_read_config_map_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test successful config map reading.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        mock_cm = mock.Mock()
        mock_cm.data = {"key": "value"}
        mock_core_v1_instance.read_namespaced_config_map.return_value = mock_cm

        k8s_client = KubernetesClient()
        result = k8s_client.read_config_map(name="test-cm", namespace="test-ns")

        assert result.data == {"key": "value"}
        mock_core_v1_instance.read_namespaced_config_map.assert_called_once_with(
            name="test-cm", namespace="test-ns"
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_read_config_map_failure(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test config map reading failure.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        mock_core_v1_instance.read_namespaced_config_map.side_effect = Exception(
            "Read failed"
        )

        k8s_client = KubernetesClient()

        with pytest.raises(KubernetesError, match="Failed to read config map"):
            k8s_client.read_config_map(name="test-cm", namespace="test-ns")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_read_secret_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test successful secret reading.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        mock_secret = mock.Mock()
        mock_secret.data = {"key": "dmFsdWU="}
        mock_core_v1_instance.read_namespaced_secret.return_value = mock_secret

        k8s_client = KubernetesClient()
        result = k8s_client.read_secret(name="test-secret", namespace="test-ns")

        assert result.data == {"key": "dmFsdWU="}
        mock_core_v1_instance.read_namespaced_secret.assert_called_once_with(
            name="test-secret", namespace="test-ns"
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_read_secret_failure(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test secret reading failure.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        mock_core_v1_instance.read_namespaced_secret.side_effect = Exception(
            "Read failed"
        )

        k8s_client = KubernetesClient()

        with pytest.raises(KubernetesError, match="Failed to read secret"):
            k8s_client.read_secret(name="test-secret", namespace="test-ns")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_service_account_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test successful service account deletion.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        k8s_client = KubernetesClient()
        k8s_client.delete_service_account(name="test-sa", namespace="test-ns")

        mock_core_v1_instance.delete_namespaced_service_account.assert_called_once_with(
            name="test-sa", namespace="test-ns"
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_service_account_not_found(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test service account deletion when resource not found (404).
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        api_exception = client.exceptions.ApiException(status=404, reason="Not Found")
        mock_core_v1_instance.delete_namespaced_service_account.side_effect = (
            api_exception
        )

        k8s_client = KubernetesClient()
        k8s_client.delete_service_account(name="test-sa", namespace="test-ns")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_service_account_api_error(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test service account deletion with API error (non-404).
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        api_exception = client.exceptions.ApiException(status=403, reason="Forbidden")
        mock_core_v1_instance.delete_namespaced_service_account.side_effect = (
            api_exception
        )

        k8s_client = KubernetesClient()

        with pytest.raises(KubernetesError, match="Failed to delete service account"):
            k8s_client.delete_service_account(name="test-sa", namespace="test-ns")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_secret_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test successful secret deletion.
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        k8s_client = KubernetesClient()
        k8s_client.delete_secret(name="test-secret", namespace="test-ns")

        mock_core_v1_instance.delete_namespaced_secret.assert_called_once_with(
            name="test-secret", namespace="test-ns"
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_secret_not_found(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        mock_core_v1_class,
        _mock_rbac_v1,
    ):
        """
        Test secret deletion when resource not found (404).
        """

        mock_core_v1_instance = mock.Mock()
        mock_core_v1_class.return_value = mock_core_v1_instance

        api_exception = client.exceptions.ApiException(status=404, reason="Not Found")
        mock_core_v1_instance.delete_namespaced_secret.side_effect = api_exception

        k8s_client = KubernetesClient()
        k8s_client.delete_secret(name="test-secret", namespace="test-ns")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_role_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        mock_rbac_v1_class,
    ):
        """
        Test successful role deletion.
        """

        mock_rbac_v1_instance = mock.Mock()
        mock_rbac_v1_class.return_value = mock_rbac_v1_instance

        k8s_client = KubernetesClient()
        k8s_client.delete_role(name="test-role", namespace="test-ns")

        mock_rbac_v1_instance.delete_namespaced_role.assert_called_once_with(
            name="test-role", namespace="test-ns"
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_role_not_found(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        mock_rbac_v1_class,
    ):
        """
        Test role deletion when resource not found (404).
        """

        mock_rbac_v1_instance = mock.Mock()
        mock_rbac_v1_class.return_value = mock_rbac_v1_instance

        api_exception = client.exceptions.ApiException(status=404, reason="Not Found")
        mock_rbac_v1_instance.delete_namespaced_role.side_effect = api_exception

        k8s_client = KubernetesClient()
        k8s_client.delete_role(name="test-role", namespace="test-ns")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_role_binding_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        mock_rbac_v1_class,
    ):
        """
        Test successful role binding deletion.
        """

        mock_rbac_v1_instance = mock.Mock()
        mock_rbac_v1_class.return_value = mock_rbac_v1_instance

        k8s_client = KubernetesClient()
        k8s_client.delete_role_binding(name="test-rb", namespace="test-ns")

        mock_rbac_v1_instance.delete_namespaced_role_binding.assert_called_once_with(
            name="test-rb", namespace="test-ns"
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_role_binding_not_found(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        mock_rbac_v1_class,
    ):
        """
        Test role binding deletion when resource not found (404).
        """

        mock_rbac_v1_instance = mock.Mock()
        mock_rbac_v1_class.return_value = mock_rbac_v1_instance

        api_exception = client.exceptions.ApiException(status=404, reason="Not Found")
        mock_rbac_v1_instance.delete_namespaced_role_binding.side_effect = api_exception

        k8s_client = KubernetesClient()
        k8s_client.delete_role_binding(name="test-rb", namespace="test-ns")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_cluster_role_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        mock_rbac_v1_class,
    ):
        """
        Test successful cluster role deletion.
        """

        mock_rbac_v1_instance = mock.Mock()
        mock_rbac_v1_class.return_value = mock_rbac_v1_instance

        k8s_client = KubernetesClient()
        k8s_client.delete_cluster_role(name="test-cr")

        mock_rbac_v1_instance.delete_cluster_role.assert_called_once_with(
            name="test-cr"
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_cluster_role_not_found(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        mock_rbac_v1_class,
    ):
        """
        Test cluster role deletion when resource not found (404).
        """

        mock_rbac_v1_instance = mock.Mock()
        mock_rbac_v1_class.return_value = mock_rbac_v1_instance

        api_exception = client.exceptions.ApiException(status=404, reason="Not Found")
        mock_rbac_v1_instance.delete_cluster_role.side_effect = api_exception

        k8s_client = KubernetesClient()
        k8s_client.delete_cluster_role(name="test-cr")

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_cluster_role_binding_success(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        mock_rbac_v1_class,
    ):
        """
        Test successful cluster role binding deletion.
        """

        mock_rbac_v1_instance = mock.Mock()
        mock_rbac_v1_class.return_value = mock_rbac_v1_instance

        k8s_client = KubernetesClient()
        k8s_client.delete_cluster_role_binding(name="test-crb")

        mock_rbac_v1_instance.delete_cluster_role_binding.assert_called_once_with(
            name="test-crb"
        )

    @mock.patch("launchpad.kubernetes.client.RbacAuthorizationV1Api")
    @mock.patch("launchpad.kubernetes.client.CoreV1Api")
    @mock.patch("launchpad.kubernetes.client.AppsV1Api")
    @mock.patch("launchpad.kubernetes.client.ApiClient")
    @mock.patch("launchpad.kubernetes.config.load_kube_config")
    @mock.patch("launchpad.kubernetes.get_logger", return_value=mock.Mock())
    def test_delete_cluster_role_binding_not_found(
        self,
        _mock_get_logger,
        _mock_load_config,
        _mock_api_client,
        _mock_apps_v1_class,
        _mock_core_v1,
        mock_rbac_v1_class,
    ):
        """
        Test cluster role binding deletion when resource not found (404).
        """

        mock_rbac_v1_instance = mock.Mock()
        mock_rbac_v1_class.return_value = mock_rbac_v1_instance

        api_exception = client.exceptions.ApiException(status=404, reason="Not Found")
        mock_rbac_v1_instance.delete_cluster_role_binding.side_effect = api_exception

        k8s_client = KubernetesClient()
        k8s_client.delete_cluster_role_binding(name="test-crb")
