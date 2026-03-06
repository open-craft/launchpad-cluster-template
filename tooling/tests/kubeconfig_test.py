"""
Tests for kubeconfig management utilities.
"""

import base64
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Set required environment variable before importing anything from launchpad
os.environ.setdefault("LAUNCHPAD_CLUSTER_DOMAIN", "test.cluster.domain")

from launchpad.exceptions import ConfigurationError
from launchpad.kubeconfig import (
    get_kubeconfig_from_env,
    get_kubeconfig_from_terraform,
    setup_kubeconfig,
)


class TestGetKubeconfigFromTerraform:
    """
    Tests for get_kubeconfig_from_terraform function.
    """

    @patch("launchpad.kubeconfig.shutil.which")
    @patch("launchpad.kubeconfig.subprocess.run")
    @patch("launchpad.kubeconfig.Path")
    def test_with_tofu_command(self, mock_path, mock_run, mock_check_command):
        """
        Test retrieval using tofu command.
        """

        mock_cwd = MagicMock()
        mock_cwd.name = "test-dir"
        mock_infrastructure = MagicMock()
        mock_infrastructure.exists.return_value = True
        mock_cwd.__truediv__.return_value = mock_infrastructure
        mock_path.cwd.return_value = mock_cwd

        mock_check_command.side_effect = lambda cmd: (
            "/usr/bin/tofu" if cmd == "tofu" else None
        )
        mock_run.return_value = Mock(
            returncode=0,
            stdout="apiVersion: v1\nkind: Config\n",
            stderr="",
        )

        result = get_kubeconfig_from_terraform()

        assert result == "apiVersion: v1\nkind: Config"
        mock_run.assert_called_once_with(
            ["tofu", "output", "-raw", "kubeconfig_content"],
            cwd=mock_infrastructure,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("launchpad.kubeconfig.shutil.which")
    @patch("launchpad.kubeconfig.subprocess.run")
    @patch("launchpad.kubeconfig.Path")
    def test_with_terraform_command(self, mock_path, mock_run, mock_check_command):
        """
        Test retrieval using terraform command when tofu not available.
        """

        mock_cwd = MagicMock()
        mock_cwd.name = "test-dir"
        mock_infrastructure = MagicMock()
        mock_infrastructure.exists.return_value = True
        mock_cwd.__truediv__.return_value = mock_infrastructure
        mock_path.cwd.return_value = mock_cwd

        mock_check_command.side_effect = lambda cmd: (
            "/usr/bin/terraform" if cmd == "terraform" else None
        )
        mock_run.return_value = Mock(
            returncode=0,
            stdout="apiVersion: v1\nkind: Config\n",
            stderr="",
        )

        result = get_kubeconfig_from_terraform()

        assert result == "apiVersion: v1\nkind: Config"
        mock_run.assert_called_once_with(
            ["terraform", "output", "-raw", "kubeconfig_content"],
            cwd=mock_infrastructure,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("launchpad.kubeconfig.shutil.which")
    def test_no_command_available(self, mock_check_command):
        """
        Test when neither tofu nor terraform is available.
        """

        mock_check_command.return_value = None

        result = get_kubeconfig_from_terraform()

        assert result is None

    @patch("launchpad.kubeconfig.shutil.which")
    @patch("launchpad.kubeconfig.subprocess.run")
    @patch("launchpad.kubeconfig.Path")
    def test_with_working_directory(self, mock_path, mock_run, mock_check_command):
        """
        Test with custom working directory.
        """

        working_dir = MagicMock()
        working_dir.name = "terraform-dir"
        mock_infrastructure = MagicMock()
        mock_infrastructure.exists.return_value = True
        working_dir.__truediv__.return_value = mock_infrastructure

        mock_check_command.side_effect = lambda cmd: (
            "/usr/bin/tofu" if cmd == "tofu" else None
        )
        mock_run.return_value = Mock(
            returncode=0,
            stdout="apiVersion: v1\nkind: Config\n",
            stderr="",
        )

        result = get_kubeconfig_from_terraform(working_dir)

        assert result == "apiVersion: v1\nkind: Config"
        mock_run.assert_called_once()
        assert mock_run.call_args[1]["cwd"] == mock_infrastructure

    @patch("launchpad.kubeconfig.shutil.which")
    @patch("launchpad.kubeconfig.subprocess.run")
    def test_command_fails(self, mock_run, mock_check_command):
        """
        Test when command execution fails.
        """

        mock_check_command.side_effect = lambda cmd: (
            "/usr/bin/tofu" if cmd == "tofu" else None
        )
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error: no kubeconfig output found",
        )

        result = get_kubeconfig_from_terraform()

        assert result is None

    @patch("launchpad.kubeconfig.shutil.which")
    @patch("launchpad.kubeconfig.subprocess.run")
    def test_empty_output(self, mock_run, mock_check_command):
        """
        Test when command returns empty output.
        """

        mock_check_command.side_effect = lambda cmd: (
            "/usr/bin/tofu" if cmd == "tofu" else None
        )
        mock_run.return_value = Mock(
            returncode=0,
            stdout="   \n  ",
            stderr="",
        )

        result = get_kubeconfig_from_terraform()

        assert result is None

    @patch("launchpad.kubeconfig.shutil.which")
    @patch("launchpad.kubeconfig.subprocess.run")
    @patch("launchpad.kubeconfig.Path")
    def test_subprocess_error(self, mock_path, mock_run, mock_check_command):
        """
        Test when subprocess raises an error.
        """

        mock_cwd = MagicMock()
        mock_cwd.name = "test-dir"
        mock_infrastructure = MagicMock()
        mock_infrastructure.exists.return_value = True
        mock_cwd.__truediv__.return_value = mock_infrastructure
        mock_path.cwd.return_value = mock_cwd

        mock_check_command.side_effect = lambda cmd: (
            "/usr/bin/tofu" if cmd == "tofu" else None
        )
        mock_run.side_effect = subprocess.SubprocessError("Command failed")

        with pytest.raises(ConfigurationError, match="Failed to execute tofu command"):
            get_kubeconfig_from_terraform()

    @patch("launchpad.kubeconfig.shutil.which")
    @patch("launchpad.kubeconfig.subprocess.run")
    @patch("launchpad.kubeconfig.Path")
    def test_whitespace_trimming(self, mock_path, mock_run, mock_check_command):
        """
        Test that whitespace is trimmed from output.
        """

        mock_cwd = MagicMock()
        mock_cwd.name = "test-dir"
        mock_infrastructure = MagicMock()
        mock_infrastructure.exists.return_value = True
        mock_cwd.__truediv__.return_value = mock_infrastructure
        mock_path.cwd.return_value = mock_cwd

        mock_check_command.side_effect = lambda cmd: (
            "/usr/bin/tofu" if cmd == "tofu" else None
        )
        mock_run.return_value = Mock(
            returncode=0,
            stdout="  \n  apiVersion: v1\nkind: Config  \n  ",
            stderr="",
        )

        result = get_kubeconfig_from_terraform()

        assert result == "apiVersion: v1\nkind: Config"


class TestGetKubeconfigFromEnv:
    """
    Tests for get_kubeconfig_from_env function.
    """

    def test_with_plain_text_env_var(self, monkeypatch):
        """
        Test retrieval of plain-text kubeconfig from environment.
        """

        kubeconfig = "apiVersion: v1\nkind: Config"
        monkeypatch.setenv("KUBECONFIG_CONTENT", kubeconfig)

        result = get_kubeconfig_from_env()

        assert result == kubeconfig

    def test_with_base64_encoded_env_var(self, monkeypatch):
        """
        Test retrieval of base64-encoded kubeconfig from environment.
        """

        kubeconfig = "apiVersion: v1\nkind: Config"
        encoded = base64.b64encode(kubeconfig.encode()).decode()
        monkeypatch.setenv("KUBECONFIG_CONTENT", encoded)

        result = get_kubeconfig_from_env()

        assert result == kubeconfig

    def test_env_var_not_set(self, monkeypatch):
        """
        Test when environment variable is not set.
        """

        monkeypatch.delenv("KUBECONFIG_CONTENT", raising=False)

        result = get_kubeconfig_from_env()

        assert result is None

    def test_empty_env_var(self, monkeypatch):
        """
        Test when environment variable is empty.
        """

        monkeypatch.setenv("KUBECONFIG_CONTENT", "")

        result = get_kubeconfig_from_env()

        assert result is None

    def test_whitespace_only_env_var(self, monkeypatch):
        """
        Test when environment variable contains only whitespace.
        """

        monkeypatch.setenv("KUBECONFIG_CONTENT", "   \n  ")

        result = get_kubeconfig_from_env()

        assert result is None

    def test_invalid_base64_treated_as_plain_text(self, monkeypatch):
        """
        Test that invalid base64 is treated as plain text.
        """

        kubeconfig = "not-base64-just-plain-text!"
        monkeypatch.setenv("KUBECONFIG_CONTENT", kubeconfig)

        result = get_kubeconfig_from_env()

        assert result == kubeconfig

    def test_multiline_kubeconfig(self, monkeypatch):
        """
        Test with multiline kubeconfig content.
        """

        kubeconfig = """apiVersion: v1
clusters:
- cluster:
    server: https://cluster.domain
  name: test-cluster
kind: Config"""
        monkeypatch.setenv("KUBECONFIG_CONTENT", kubeconfig)

        result = get_kubeconfig_from_env()

        assert result == kubeconfig


class TestSetupKubeconfig:
    """
    Tests for setup_kubeconfig function.
    """

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    def test_with_terraform_kubeconfig(self, mock_get_terraform):
        """
        Test setup using kubeconfig from Terraform.
        """
        mock_get_terraform.return_value = "kubeconfig from terraform"

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("launchpad.kubeconfig.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)

                setup_kubeconfig()

                kubeconfig_path = Path(tmpdir) / ".kube" / "config"
                assert kubeconfig_path.exists()
                assert kubeconfig_path.read_text() == "kubeconfig from terraform"

                assert oct(kubeconfig_path.stat().st_mode)[-3:] == "600"

        mock_get_terraform.assert_called_once_with(None)

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    @patch("launchpad.kubeconfig.get_kubeconfig_from_env")
    def test_with_env_kubeconfig(self, mock_get_env, mock_get_terraform):
        """
        Test setup using kubeconfig from environment when Terraform fails.
        """
        mock_get_terraform.return_value = None
        mock_get_env.return_value = "kubeconfig from env"

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("launchpad.kubeconfig.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)

                setup_kubeconfig()

                kubeconfig_path = Path(tmpdir) / ".kube" / "config"
                assert kubeconfig_path.exists()
                assert kubeconfig_path.read_text() == "kubeconfig from env"

                assert oct(kubeconfig_path.stat().st_mode)[-3:] == "600"

        mock_get_terraform.assert_called_once()
        mock_get_env.assert_called_once()

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    @patch("launchpad.kubeconfig.get_kubeconfig_from_env")
    def test_with_existing_kubeconfig(self, mock_get_env, mock_get_terraform):
        """
        Test when existing kubeconfig is available and no new one is provided.
        """

        mock_get_terraform.return_value = None
        mock_get_env.return_value = None

        with patch("launchpad.kubeconfig.Path") as mock_path_class:
            mock_home = MagicMock()
            mock_kubeconfig_path = MagicMock()
            mock_kubeconfig_path.exists.return_value = True

            mock_path_class.home.return_value = mock_home
            mock_home.__truediv__.return_value = mock_kubeconfig_path

            setup_kubeconfig()

        mock_get_terraform.assert_called_once()
        mock_get_env.assert_called_once()

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    @patch("launchpad.kubeconfig.get_kubeconfig_from_env")
    def test_no_kubeconfig_available(self, mock_get_env, mock_get_terraform):
        """
        Test when no kubeconfig is available from any source.
        """

        mock_get_terraform.return_value = None
        mock_get_env.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("launchpad.kubeconfig.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)

                with pytest.raises(ConfigurationError, match="No kubeconfig available"):
                    setup_kubeconfig()

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    @patch("launchpad.kubeconfig.get_kubeconfig_from_env")
    def test_force_env_skips_terraform(self, mock_get_env, mock_get_terraform):
        """
        Test that when terraform returns None, env is used as fallback.
        """
        mock_get_terraform.return_value = None
        mock_get_env.return_value = "kubeconfig from env"

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("launchpad.kubeconfig.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)

                setup_kubeconfig()

                kubeconfig_path = Path(tmpdir) / ".kube" / "config"
                assert kubeconfig_path.exists()
                assert kubeconfig_path.read_text() == "kubeconfig from env"

        mock_get_terraform.assert_called_once()

        mock_get_env.assert_called_once()

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    def test_with_custom_terraform_dir(self, mock_get_terraform):
        """
        Test setup with custom Terraform directory.
        """
        mock_get_terraform.return_value = "kubeconfig content"
        terraform_dir = Path("/custom/terraform/dir")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("launchpad.kubeconfig.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)

                setup_kubeconfig(terraform_dir=terraform_dir)

                kubeconfig_path = Path(tmpdir) / ".kube" / "config"
                assert kubeconfig_path.exists()
                assert kubeconfig_path.read_text() == "kubeconfig content"

        mock_get_terraform.assert_called_once_with(terraform_dir)

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    def test_write_error_handling(self, mock_get_terraform):
        """
        Test error handling when writing kubeconfig fails.
        """
        mock_get_terraform.return_value = "kubeconfig content"

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("launchpad.kubeconfig.Path.home") as mock_home:
                mock_home.return_value = Path(tmpdir)

                kube_dir = Path(tmpdir) / ".kube"
                kube_dir.mkdir()
                kube_dir.chmod(0o444)

                with pytest.raises(
                    ConfigurationError, match="Failed to write kubeconfig"
                ):
                    setup_kubeconfig()

                kube_dir.chmod(0o755)

    def test_integration_with_real_tempfile(self):
        """
        Integration test using real temporary directory.
        """

        kubeconfig_content = "apiVersion: v1\nkind: Config"

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "launchpad.kubeconfig.get_kubeconfig_from_terraform"
            ) as mock_terraform:
                mock_terraform.return_value = kubeconfig_content

                with patch("launchpad.kubeconfig.Path.home") as mock_home:
                    mock_home.return_value = Path(tmpdir)

                    setup_kubeconfig()

                    kubeconfig_path = Path(tmpdir) / ".kube" / "config"
                    assert kubeconfig_path.exists()
                    assert kubeconfig_path.read_text() == kubeconfig_content

                    assert oct(kubeconfig_path.stat().st_mode)[-3:] == "600"
