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

MINIMAL_KUBECONFIG = "apiVersion: v1\nkind: Config"


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
            returncode=0, stdout=f"{MINIMAL_KUBECONFIG}\n", stderr=""
        )

        result = get_kubeconfig_from_terraform()

        assert result == MINIMAL_KUBECONFIG
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
            returncode=0, stdout=f"{MINIMAL_KUBECONFIG}\n", stderr=""
        )

        result = get_kubeconfig_from_terraform()

        assert result == MINIMAL_KUBECONFIG
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
    def test_with_working_directory(self, _mock_path, mock_run, mock_check_command):
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
            returncode=0, stdout=f"{MINIMAL_KUBECONFIG}\n", stderr=""
        )

        result = get_kubeconfig_from_terraform(working_dir)

        assert result == MINIMAL_KUBECONFIG
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
            returncode=0, stdout=f"  \n  {MINIMAL_KUBECONFIG}  \n  ", stderr=""
        )

        result = get_kubeconfig_from_terraform()

        assert result == MINIMAL_KUBECONFIG


class TestGetKubeconfigFromEnv:
    """
    Tests for get_kubeconfig_from_env function.
    """

    def test_with_plain_text_env_var(self, monkeypatch):
        """
        Test retrieval of plain-text kubeconfig from environment.
        """

        kubeconfig = MINIMAL_KUBECONFIG
        monkeypatch.setenv("KUBECONFIG_CONTENT", kubeconfig)

        result = get_kubeconfig_from_env()

        assert result == kubeconfig

    def test_with_base64_encoded_env_var(self, monkeypatch):
        """
        Test retrieval of base64-encoded kubeconfig from environment.
        """

        kubeconfig = MINIMAL_KUBECONFIG
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

    @pytest.fixture(autouse=True)
    def _isolate_kubeconfig_env(self, monkeypatch):
        monkeypatch.delenv("KUBECONFIG", raising=False)
        monkeypatch.delenv("KUBECONFIG_CONTENT", raising=False)

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    def test_with_terraform_kubeconfig(self, mock_get_terraform):
        """
        Test setup using kubeconfig from Terraform.
        """
        mock_get_terraform.return_value = "kubeconfig from terraform"

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "infrastructure").mkdir(parents=True)
            with patch("launchpad.kubeconfig.Path.cwd", return_value=root):
                setup_kubeconfig()

            kubeconfig_path = root / "infrastructure" / ".kubeconfig"
            assert kubeconfig_path.exists()
            assert (
                kubeconfig_path.read_text(encoding="utf-8")
                == "kubeconfig from terraform"
            )
            assert oct(kubeconfig_path.stat().st_mode)[-3:] == "600"
            assert os.environ["KUBECONFIG"] == str(kubeconfig_path.resolve())

        mock_get_terraform.assert_called_once_with(None)

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    @patch("launchpad.kubeconfig.get_kubeconfig_from_env")
    def test_with_env_kubeconfig(self, mock_get_env, mock_get_terraform):
        """
        Test setup uses KUBECONFIG_CONTENT before Terraform output.
        """
        mock_get_env.return_value = "kubeconfig from env"
        mock_get_terraform.return_value = "kubeconfig from terraform"

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with patch("launchpad.kubeconfig.Path.cwd", return_value=root):
                setup_kubeconfig()

            written = Path(os.environ["KUBECONFIG"])
            assert written.exists()
            assert written.read_text(encoding="utf-8") == "kubeconfig from env"
            assert oct(written.stat().st_mode)[-3:] == "600"

        mock_get_terraform.assert_not_called()
        mock_get_env.assert_called_once()

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    @patch("launchpad.kubeconfig.get_kubeconfig_from_env")
    def test_short_circuits_when_kubeconfig_env_usable(
        self, mock_get_env, mock_get_terraform, tmp_path, monkeypatch
    ):
        """
        When KUBECONFIG points at an existing file, do not fetch or write other sources.
        """
        kube_file = tmp_path / "existing.yaml"
        kube_file.write_text("apiVersion: v1\nkind: Config\n", encoding="utf-8")
        monkeypatch.setenv("KUBECONFIG", str(kube_file))

        mock_get_terraform.return_value = None
        mock_get_env.return_value = None

        setup_kubeconfig()

        mock_get_terraform.assert_not_called()
        mock_get_env.assert_not_called()

    def test_kubeconfig_env_multiple_paths_second_usable(self, tmp_path, monkeypatch):
        """
        KUBECONFIG may list several paths (os.pathsep); the first existing file wins.
        """
        missing = tmp_path / "missing.yaml"
        existing = tmp_path / "exists.yaml"
        existing.write_text("apiVersion: v1\nkind: Config\n", encoding="utf-8")
        monkeypatch.setenv("KUBECONFIG", f"{missing}{os.pathsep}{existing}")

        with patch("launchpad.kubeconfig.get_kubeconfig_from_terraform") as mock_tf:
            with patch("launchpad.kubeconfig.get_kubeconfig_from_env") as mock_env:
                setup_kubeconfig()
                mock_tf.assert_not_called()
                mock_env.assert_not_called()

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    @patch("launchpad.kubeconfig.get_kubeconfig_from_env")
    def test_no_kubeconfig_available(self, mock_get_env, mock_get_terraform):
        """
        Test when no kubeconfig is available from any source.
        """

        mock_get_terraform.return_value = None
        mock_get_env.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with patch("launchpad.kubeconfig.Path.cwd", return_value=root):
                with pytest.raises(
                    ConfigurationError, match="Set KUBECONFIG to an existing"
                ):
                    setup_kubeconfig()

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    @patch("launchpad.kubeconfig.get_kubeconfig_from_env")
    def test_prefers_env_over_terraform_output(self, mock_get_env, mock_get_terraform):
        """
        Test that env kubeconfig is used even when Terraform would provide one.
        """
        mock_get_env.return_value = "kubeconfig from env"
        mock_get_terraform.return_value = "kubeconfig from terraform"

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with patch("launchpad.kubeconfig.Path.cwd", return_value=root):
                setup_kubeconfig()

            written = Path(os.environ["KUBECONFIG"])
            assert written.exists()
            assert written.read_text(encoding="utf-8") == "kubeconfig from env"

        mock_get_terraform.assert_not_called()
        mock_get_env.assert_called_once()

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    def test_with_custom_terraform_dir(self, mock_get_terraform):
        """
        Test setup with custom Terraform directory.
        """
        mock_get_terraform.return_value = "kubeconfig content"
        terraform_dir = Path("/custom/terraform/dir")

        with patch("launchpad.kubeconfig.Path.cwd", return_value=Path.cwd()):
            setup_kubeconfig(terraform_dir=terraform_dir)

        written = Path(os.environ["KUBECONFIG"])
        assert written.exists()
        assert written.read_text(encoding="utf-8") == "kubeconfig content"

        mock_get_terraform.assert_called_once_with(terraform_dir)

    @patch("launchpad.kubeconfig.get_kubeconfig_from_terraform")
    def test_write_error_handling(self, mock_get_terraform):
        """
        Test error handling when writing kubeconfig fails.
        """
        mock_get_terraform.return_value = "kubeconfig content"

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            infra = root / "infrastructure"
            infra.mkdir(parents=True)
            infra.chmod(0o444)
            try:
                with patch("launchpad.kubeconfig.Path.cwd", return_value=root):
                    with pytest.raises(
                        ConfigurationError, match="Failed to write kubeconfig"
                    ):
                        setup_kubeconfig()
            finally:
                infra.chmod(0o755)

    def test_integration_with_real_tempfile(self):
        """
        Integration test using real temporary directory.
        """

        kubeconfig_content = MINIMAL_KUBECONFIG

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "infrastructure").mkdir(parents=True)
            with patch(
                "launchpad.kubeconfig.get_kubeconfig_from_terraform"
            ) as mock_terraform:
                mock_terraform.return_value = kubeconfig_content

                with patch("launchpad.kubeconfig.Path.cwd", return_value=root):
                    setup_kubeconfig()

                kubeconfig_path = root / "infrastructure" / ".kubeconfig"
                assert kubeconfig_path.exists()
                assert kubeconfig_path.read_text(encoding="utf-8") == kubeconfig_content

                assert oct(kubeconfig_path.stat().st_mode)[-3:] == "600"
