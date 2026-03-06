"""
Kubeconfig management utilities.

This module provides functionality to retrieve and configure Kubernetes
configuration from various sources including Terraform/OpenTofu outputs
and environment variables.
"""

import base64
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from launchpad.exceptions import ConfigurationError
from launchpad.utils import get_logger

logger = None


def _get_logger():
    global logger  # pylint: disable=global-statement
    if logger is None:
        logger = get_logger(__name__)
    return logger


def get_kubeconfig_from_terraform(working_dir: Optional[Path] = None) -> Optional[str]:
    """
    Retrieve kubeconfig from Terraform/OpenTofu output.

    Checks for tofu first, then terraform. Executes the appropriate command
    to retrieve the kubeconfig output value.

    Args:
        working_dir: Directory where Terraform/OpenTofu files are located.
                    Defaults to current directory.

    Returns:
        Kubeconfig content as string, or None if command not available
        or output not found

    Raises:
        ConfigurationError: If command execution fails
    """

    command = None
    if shutil.which("tofu"):
        command = "tofu"
        _get_logger().debug("Found tofu command")
    elif shutil.which("terraform"):
        command = "terraform"
        _get_logger().debug("Found terraform command")
    else:
        _get_logger().debug("Neither tofu nor terraform commands found")
        return None

    if not working_dir:
        working_dir = Path.cwd()

    # If we're already in the infrastructure directory, go up one level
    if working_dir.name == "infrastructure":
        working_dir = working_dir.parent

    # Check if infrastructure directory exists in the current working directory
    infrastructure_dir = working_dir / "infrastructure"
    if not infrastructure_dir.exists():
        _get_logger().warning("Infrastructure directory not found in %s", working_dir)
        return None

    try:
        _get_logger().info("Getting kubeconfig from %s", infrastructure_dir)
        _get_logger().info(
            "Command: %s", [command, "output", "-raw", "kubeconfig_content"]
        )
        result = subprocess.run(
            [command, "output", "-raw", "kubeconfig_content"],
            cwd=infrastructure_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except subprocess.SubprocessError as exc:
        raise ConfigurationError(f"Failed to execute {command} command: {exc}") from exc

    if result.returncode != 0:
        _get_logger().debug(
            "Failed to get kubeconfig from %s: %s", command, result.stderr
        )
        return None

    kubeconfig = result.stdout.strip()
    if not kubeconfig:
        _get_logger().debug("Empty kubeconfig from %s output", command)
        return None

    _get_logger().debug("Raw output from %s: %s", command, repr(kubeconfig[:100]))

    # Check if the output looks like a valid kubeconfig
    if (
        not (kubeconfig.startswith("apiVersion:") and "kind: Config" in kubeconfig)
        or kubeconfig.startswith("\x1b[")
        or "Warning:" in kubeconfig
    ):
        _get_logger().warning(
            "Output from %s does not appear to be a valid kubeconfig", command
        )
        _get_logger().warning(
            "Validation failed - starts with apiVersion: %s, contains kind: Config: %s, starts with \\x1b[: %s, contains Warning: %s",
            kubeconfig.startswith("apiVersion:"),
            "kind: Config" in kubeconfig,
            kubeconfig.startswith("\x1b["),
            "Warning:" in kubeconfig,
        )
        return None

    _get_logger().info("Successfully retrieved kubeconfig from %s", command)
    return kubeconfig


def get_kubeconfig_from_env() -> Optional[str]:
    """
    Retrieve kubeconfig from environment variable.

    Checks KUBECONFIG_CONTENT environment variable for base64-encoded
    or plain kubeconfig content.

    Returns:
        Kubeconfig content as string, or None if not found
    """
    kubeconfig_content = os.environ.get("KUBECONFIG_CONTENT", "").strip()

    if not kubeconfig_content:
        _get_logger().debug("KUBECONFIG_CONTENT environment variable not set")
        return None

    try:
        decoded = base64.b64decode(kubeconfig_content, validate=True).decode("utf-8")
        _get_logger().info(
            "Successfully decoded base64-encoded kubeconfig from environment"
        )
        return decoded
    except Exception:  # pylint: disable=broad-except
        _get_logger().info("Using plain-text kubeconfig from environment")
        return kubeconfig_content


def setup_kubeconfig(terraform_dir: Optional[Path] = None) -> None:
    """
    Set up kubeconfig from available sources.

    Attempts to retrieve kubeconfig in the following order:
    1. Terraform/OpenTofu output (if not force_env)
    2. KUBECONFIG_CONTENT environment variable
    3. Use existing kubeconfig if available

    If kubeconfig is retrieved, it is written to ~/.kube/config.

    Args:
        terraform_dir: Directory containing Terraform/OpenTofu files.
                      If None, uses current directory.

    Raises:
        ConfigurationError: If no valid kubeconfig can be obtained
    """
    kubeconfig_content = None

    # Try Terraform/OpenTofu first
    kubeconfig_content = get_kubeconfig_from_terraform(terraform_dir)

    # Fall back to environment variable
    if not kubeconfig_content:
        kubeconfig_content = get_kubeconfig_from_env()

    # Check if existing kubeconfig is available
    kubeconfig_path = Path.home() / ".kube" / "config"
    if not kubeconfig_content:
        if kubeconfig_path.exists():
            _get_logger().info("Using existing kubeconfig at %s", kubeconfig_path)
            return

        raise ConfigurationError(
            "No kubeconfig available. Please ensure one of the following:\n"
            "1. Run this command from a directory with infrastructure directory present\n"
            "2. Set KUBECONFIG_CONTENT environment variable\n"
            "3. Have a valid kubeconfig at ~/.kube/config"
        )

    try:
        kubeconfig_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=kubeconfig_path.parent
        ) as tmp_file:
            tmp_file.write(kubeconfig_content)
            tmp_path = Path(tmp_file.name)

        tmp_path.chmod(0o600)
        tmp_path.replace(kubeconfig_path)

        _get_logger().info("Kubeconfig written to %s", kubeconfig_path)

    except (OSError, IOError) as exc:
        raise ConfigurationError(f"Failed to write kubeconfig: {exc}") from exc
