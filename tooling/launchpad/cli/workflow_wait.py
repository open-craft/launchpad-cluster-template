"""
Shared helpers for waiting on Argo Workflows.
"""

import logging
import subprocess

DEFAULT_WORKFLOW_TIMEOUT = 300


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
