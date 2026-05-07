"""
Utility functions for CLI.
"""

import logging
import subprocess
import sys
from typing import Callable, TypeVar

DEFAULT_WORKFLOW_TIMEOUT = 300

T = TypeVar("T")


def wait_for_workflow_completion(
    instance_name: str,
    workflow_name: str,
    logger: logging.Logger,
    timeout: int = DEFAULT_WORKFLOW_TIMEOUT,
) -> bool:
    """
    Wait for an Argo Workflow to complete and check its status.

    Args:
        instance_name: Namespace where the workflow runs
        workflow_name: Name of the workflow to wait for
        logger: Logger used for status output
        timeout: Maximum time to wait in seconds

    Returns:
        True if workflow succeeded, False otherwise
    """
    logger.debug("Waiting for workflow '%s' to complete...", workflow_name)

    try:
        subprocess.run(
            [
                "kubectl",
                "wait",
                "--for=condition=Completed",
                f"workflow/{workflow_name}",
                "-n",
                instance_name,
                f"--timeout={timeout}s",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        result = subprocess.run(
            [
                "kubectl",
                "get",
                f"workflow/{workflow_name}",
                "-n",
                instance_name,
                "-o",
                "jsonpath={.status.phase}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        status = result.stdout.strip()

        if status == "Succeeded":
            logger.debug("Workflow '%s' succeeded", workflow_name)
            return True

        logger.warning("Workflow '%s' failed with status: %s", workflow_name, status)
        return False

    except subprocess.CalledProcessError:
        logger.warning("Workflow '%s' timed out or failed", workflow_name)
        return False


def run_command_with_logging(
    logger: logging.Logger, description: str, func: Callable[..., T], *args, **kwargs
) -> T:
    """
    Run a command with logging for CLI operations.

    This is specifically for CLI commands to provide user-friendly output.
    Internal library code should do its own logging.

    Args:
        logger: Logger instance
        description: Description of the command (will be capitalized and logged)
        func: Function to run
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of the function

    Raises:
        Exception: If the command fails
    """

    logger.info(description)

    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error("Failed to %s: %s", description, e)
        raise


def exit_with_error(
    logger: logging.Logger, message: str, exc_info: bool = True
) -> None:
    """
    Exit with error.

    Args:
        message: Error message
        exc_info: Whether to include exception information

    Returns:
        None
    """

    logger.error(message, exc_info=exc_info)
    sys.exit(1)
