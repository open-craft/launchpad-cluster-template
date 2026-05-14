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
from typing import List, Optional

from launchpad.exceptions import ConfigurationError
from launchpad.utils import get_logger

logger = get_logger(__name__)


def _get_terraform_command() -> Optional[str]:
    if shutil.which("tofu"):
        logger.debug("Found tofu command")
        return "tofu"

    if shutil.which("terraform"):
        logger.debug("Found terraform command")
        return "terraform"

    logger.debug("Neither tofu nor terraform commands found")
    return None


def _kubeconfig_paths_from_env() -> List[Path]:
    raw = os.environ.get("KUBECONFIG", "")
    if not raw.strip():
        return []

    return [
        Path(entry.strip()).expanduser()
        for entry in raw.split(os.pathsep)
        if entry.strip()
    ]


def _has_usable_kubeconfig_env() -> bool:
    for path in _kubeconfig_paths_from_env():
        try:
            if path.is_file():
                logger.info("Using kubeconfig from KUBECONFIG entry %s", path)
                return True
        except OSError:
            continue

    return False


def _atomic_write_file(path: Path, content: str) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            dir=parent,
            prefix=".tmp-kubeconfig-",
            encoding="utf-8",
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)

        tmp_path.chmod(0o600)
        tmp_path.replace(path)
    except OSError:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _resolve_infrastructure_dir(working_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Resolve the infrastructure directory used for Terraform/OpenTofu and kubeconfig files.

    Args:
        working_dir: Repository or project root (directory that contains ``infrastructure/``).
            Defaults to the current working directory.

    Returns:
        Path to ``infrastructure`` if it exists, otherwise None.
    """
    if not working_dir:
        working_dir = Path.cwd()

    if working_dir.name == "infrastructure":
        working_dir = working_dir.parent

    infrastructure_dir = working_dir / "infrastructure"
    if not infrastructure_dir.is_dir():
        return None

    return infrastructure_dir


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

    command = _get_terraform_command()
    if not command:
        return None

    infrastructure_dir = _resolve_infrastructure_dir(working_dir)
    if not infrastructure_dir:
        logger.warning(
            "Infrastructure directory not found for working dir %s",
            working_dir or Path.cwd(),
        )
        return None

    try:
        logger.info("Getting kubeconfig from %s", infrastructure_dir)
        logger.info("Command: %s", [command, "output", "-raw", "kubeconfig_content"])
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
        logger.debug("Failed to get kubeconfig from %s: %s", command, result.stderr)
        return None

    kubeconfig = result.stdout.strip()
    if not kubeconfig:
        logger.debug("Empty kubeconfig from %s output", command)
        return None

    logger.debug("Raw output from %s: %s", command, repr(kubeconfig[:100]))

    # Check if the output looks like a valid kubeconfig
    if (
        not (kubeconfig.startswith("apiVersion:") and "kind: Config" in kubeconfig)
        or kubeconfig.startswith("\x1b[")
        or "Warning:" in kubeconfig
    ):
        logger.warning(
            "Output from %s does not appear to be a valid kubeconfig", command
        )
        logger.warning(
            "Validation failed - starts with apiVersion: %s, contains kind: Config: %s, starts with \\x1b[: %s, contains Warning: %s",
            kubeconfig.startswith("apiVersion:"),
            "kind: Config" in kubeconfig,
            kubeconfig.startswith("\x1b["),
            "Warning:" in kubeconfig,
        )
        return None

    logger.info("Successfully retrieved kubeconfig from %s", command)
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
        logger.debug("KUBECONFIG_CONTENT environment variable not set")
        return None

    try:
        decoded = base64.b64decode(kubeconfig_content, validate=True).decode("utf-8")
        logger.info("Successfully decoded base64-encoded kubeconfig from environment")
        return decoded
    except Exception:  # pylint: disable=broad-except
        logger.info("Using plain-text kubeconfig from environment")
        return kubeconfig_content


def setup_kubeconfig(terraform_dir: Optional[Path] = None) -> None:
    """
    Set up kubeconfig from available sources for this process.

    Resolution order:

    1. If ``KUBECONFIG`` is set and any path in it (split with ``os.pathsep``) is an
       existing regular file, use that and return without writing or mutating sources.
    2. ``KUBECONFIG_CONTENT`` environment variable (plain or base64).
    3. Terraform/OpenTofu ``kubeconfig_content`` output (from ``infrastructure/``).

    When content comes from (2) or (3), it is written to either
    ``infrastructure/.kubeconfig`` when an infrastructure directory
    exists, or a private file under the system temporary directory. The process
    environment variable ``KUBECONFIG`` is then set to that file's absolute path so
    ``kubectl`` and client-go (``load_kube_config``) use it. This avoids overwriting
    ``~/.kube/config``.

    Args:
        terraform_dir: Directory containing Terraform/OpenTofu files (repository root
            or ``infrastructure`` parent). If None, uses the current working directory.

    Raises:
        ConfigurationError: If no valid kubeconfig can be obtained
    """
    if _has_usable_kubeconfig_env():
        return

    kubeconfig_content = get_kubeconfig_from_env()

    if not kubeconfig_content:
        kubeconfig_content = get_kubeconfig_from_terraform(terraform_dir)

    if not kubeconfig_content:
        raise ConfigurationError(
            "No kubeconfig available. Please ensure one of the following:\n"
            "1. Run this command from a directory with an infrastructure directory present\n"
            "   (so Terraform/OpenTofu can provide kubeconfig), or\n"
            "2. Set KUBECONFIG_CONTENT environment variable, or\n"
            "3. Set KUBECONFIG to an existing kubeconfig file path for your cluster"
        )

    infrastructure_dir = _resolve_infrastructure_dir(terraform_dir)
    if infrastructure_dir:
        kubeconfig_path = infrastructure_dir / ".kubeconfig"
    else:
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            prefix="launchpad-kubeconfig-",
            suffix=".yaml",
            encoding="utf-8",
        ) as tmp_file:
            kubeconfig_path = Path(tmp_file.name)

    try:
        _atomic_write_file(kubeconfig_path, kubeconfig_content)
    except (OSError, IOError) as exc:
        raise ConfigurationError(f"Failed to write kubeconfig: {exc}") from exc

    os.environ["KUBECONFIG"] = str(kubeconfig_path.resolve())
    logger.info("Kubeconfig written to %s", kubeconfig_path)
