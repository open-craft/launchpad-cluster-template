"""
Instance delete command.
"""

import argparse
import subprocess
import time
from pathlib import Path

from launchpad.cli.utils import exit_with_error, run_command_with_logging
from launchpad.cli.workflow_wait import wait_for_workflow_completion
from launchpad.config import get_config
from launchpad.exceptions import KubernetesError
from launchpad.kubeconfig import setup_kubeconfig
from launchpad.kubernetes import KubernetesClient
from launchpad.utils import (
    check_command_installed,
    get_logger,
    load_application_config,
    load_instance_config,
    log_success,
)

logger = get_logger(__name__)

NAMESPACE_DELETE_RETRY = 3
NAMESPACE_DELETE_TIMEOUT = 300
NAMESPACE_DELETE_POLL_INTERVAL = 3.0


def _wait_for_namespace_absent(
    instance_name: str,
    timeout_s: int = NAMESPACE_DELETE_TIMEOUT,
    poll_interval_s: float = NAMESPACE_DELETE_POLL_INTERVAL,
) -> None:
    """
    Poll until the namespace is no longer returned by the API (fully removed or never existed).

    Success is defined by the API no longer listing the namespace, not by ``kubectl delete`` exit
    codes (which can be non-zero on client timeouts even while termination is still progressing).
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["kubectl", "get", "namespace", instance_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.debug(
                "Namespace '%s' is no longer present in the API", instance_name
            )
            return
        time.sleep(poll_interval_s)

    subprocess.run(["kubectl", "get", "namespace", instance_name], check=False)
    raise KubernetesError(
        f"Timed out after {timeout_s}s waiting for namespace '{instance_name}' to be removed"
    )


def _delete_namespace_with_retry(instance_name: str) -> None:
    """
    Request namespace deletion and wait until it disappears, with retries.

    Re-issues ``kubectl delete`` between rounds in case the first wait exhausts while the
    namespace is still terminating (common with finalizers); a later round often completes once
    dependents have drained.
    """
    last_wait_error: KubernetesError | None = None

    for round_num in range(1, NAMESPACE_DELETE_RETRY + 1):
        delete_result = subprocess.run(
            [
                "kubectl",
                "delete",
                "namespace",
                instance_name,
                "--wait=false",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if delete_result.returncode != 0:
            combined = (delete_result.stderr or "") + (delete_result.stdout or "")
            if "NotFound" in combined or "not found" in combined.lower():
                logger.debug(
                    "Namespace '%s' was already gone before delete (or race); verifying...",
                    instance_name,
                )
            else:
                logger.warning(
                    "kubectl delete namespace returned exit code %s (round %s/%s); "
                    "waiting for namespace to disappear from the API. Output: %s",
                    delete_result.returncode,
                    round_num,
                    NAMESPACE_DELETE_RETRY,
                    combined.strip() or "(empty)",
                )

        try:
            _wait_for_namespace_absent(
                instance_name,
                timeout_s=NAMESPACE_DELETE_TIMEOUT,
            )
            return
        except KubernetesError as exc:
            last_wait_error = exc
            if round_num >= NAMESPACE_DELETE_RETRY:
                break
            logger.warning(
                "Namespace '%s' still present after %s s (round %s/%s); "
                "re-checking status and re-issuing delete",
                instance_name,
                NAMESPACE_DELETE_TIMEOUT,
                round_num,
                NAMESPACE_DELETE_RETRY,
            )
            subprocess.run(
                ["kubectl", "get", "namespace", instance_name, "-o", "wide"],
                check=False,
            )

    raise KubernetesError(
        f"Failed to delete namespace '{instance_name}'"
    ) from last_wait_error


def _create_deprovision_workflows(
    k8s_client: KubernetesClient,
    instance_name: str,
    manifests_url: str,
    instance_config: dict,
) -> None:
    """
    Create and execute deprovision workflows for MySQL, MongoDB, and Storage.

    Args:
        k8s_client: Kubernetes client
        instance_name: Name of the instance
        manifests_url: Base URL for manifest files
        instance_config: Configuration dictionary for the instance
    """
    logger.info("Creating deprovision workflows for instance '%s'", instance_name)

    workflows = [
        (
            "MySQL",
            "launchpad-mysql-deprovision-workflow.yml",
            f"mysql-deprovision-{instance_name}",
        ),
        (
            "MongoDB",
            "launchpad-mongodb-deprovision-workflow.yml",
            f"mongodb-deprovision-{instance_name}",
        ),
        (
            "Storage",
            "launchpad-storage-deprovision-workflow.yml",
            f"storage-deprovision-{instance_name}",
        ),
    ]

    for workflow_type, manifest_file, workflow_name in workflows:
        try:
            run_command_with_logging(
                logger,
                f"apply {workflow_type} deprovision workflow",
                k8s_client.apply_manifest_from_url,
                f"{manifests_url}/{manifest_file}",
                instance_name,
                instance_config,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Failed to apply %s deprovision workflow (this may be expected if resources don't exist): %s",
                workflow_type,
                e,
            )

    logger.info("Waiting for deprovision workflows to complete...")
    failed_workflows: list[str] = []

    for workflow_type, _, workflow_name in workflows:
        if not wait_for_workflow_completion(
            instance_name, workflow_name, logger=logger
        ):
            failed_workflows.append(workflow_type)

    subprocess.run(
        ["kubectl", "get", "workflows", "-n", instance_name],
        check=False,
    )

    if failed_workflows:
        raise KubernetesError(
            "Deprovision workflow(s) did not succeed: "
            f"{', '.join(failed_workflows)}. "
            "See workflow logs in the instance namespace; the delete was aborted so "
            "cloud resources are not left behind without a failed CI signal."
        )

    logger.warning("Cleaning up workflows to save resources...")
    for _, _, workflow_name in workflows:
        subprocess.run(
            ["kubectl", "delete", "workflow", workflow_name, "-n", instance_name],
            check=False,
            capture_output=True,
        )

    log_success(
        logger,
        f"Deprovision workflows created and completed for instance '{instance_name}'",
    )


def _delete_argocd_application(instance_name: str) -> None:
    """
    Delete ArgoCD Application for the instance.

    Args:
        instance_name: Name of the instance
    """
    logger.info("Deleting ArgoCD Application for instance '%s'", instance_name)

    application_config = load_application_config(instance_name)
    metadata = application_config.get("metadata", {})

    result = subprocess.run(
        [
            "kubectl",
            "delete",
            "application",
            metadata.get("name"),
            "-n",
            metadata.get("namespace"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        logger.warning("ArgoCD Application not found (may have been deleted already)")


def _cleanup_rbac(instance_name: str) -> None:
    """
    Clean up RBAC resources for the instance.

    Args:
        instance_name: Name of the instance
    """
    logger.info("Cleaning up RBAC resources for instance '%s'", instance_name)

    resources = [
        ("clusterrole", f"{instance_name}-workflows"),
        ("clusterrolebinding", f"{instance_name}-binding"),
    ]

    for resource_type, resource_name in resources:
        subprocess.run(
            ["kubectl", "delete", resource_type, resource_name],
            capture_output=True,
            check=False,
        )


def _delete_provision_workflows(instance_name: str) -> None:
    """
    Delete provision workflows if they still exist.

    Args:
        instance_name: Name of the instance
    """
    logger.info("Deleting provision workflows for instance '%s'", instance_name)

    workflows = [
        f"mysql-provision-{instance_name}",
        f"mongodb-provision-{instance_name}",
        f"storage-provision-{instance_name}",
    ]

    for workflow_name in workflows:
        subprocess.run(
            ["kubectl", "delete", "workflow", workflow_name, "-n", instance_name],
            capture_output=True,
            check=False,
        )


def delete_instance(instance_name: str, force: bool = False) -> None:
    """
    Delete an OpenEdX instance and all associated resources.

    This orchestrates:
    - Deleting provision workflows
    - Creating and running deprovision workflows
    - Deleting ArgoCD application
    - Cleaning up RBAC resources
    - Deleting namespace
    - Removing instance directory

    Args:
        instance_name: Name of the instance to delete
        force: Skip confirmation prompt

    Raises:
        KubernetesError: If instance deletion fails
        subprocess.CalledProcessError: If external commands fail
    """
    logger.info(
        "Starting deletion of instance '%s' and all associated resources", instance_name
    )
    logger.warning("This will permanently remove the instance and all its data")

    if not force:
        confirm = input(
            f"Are you sure you want to delete instance '{instance_name}'? (y/N): "
        )
        if confirm.lower() not in ["y", "yes"]:
            logger.info("Instance deletion cancelled")
            return

    check_command_installed("kubectl")

    config = get_config()

    result = subprocess.run(
        ["kubectl", "get", "namespace", instance_name],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        logger.warning("Namespace '%s' does not exist", instance_name)
    else:
        k8s_client = KubernetesClient()
        manifests_url = (
            # pylint: disable=no-member
            config.cluster.opencraft_manifests_url
        )

        instance_config = load_instance_config(instance_name, logger)

        _delete_provision_workflows(instance_name)

        _create_deprovision_workflows(
            k8s_client, instance_name, manifests_url, instance_config
        )

        _delete_argocd_application(instance_name)

        _cleanup_rbac(instance_name)

        logger.info("Deleting namespace '%s' and all its resources...", instance_name)

        _delete_namespace_with_retry(instance_name)

        log_success(logger, f"Namespace '{instance_name}' successfully deleted")

    instances_dir = Path(
        # pylint: disable=no-member
        config.cluster.instances_directory
    )
    instance_dir = instances_dir / instance_name

    if instance_dir.exists():
        logger.info("Removing instance directory: %s", instance_dir)
        subprocess.run(["rm", "-rf", str(instance_dir)], check=False)

    log_success(logger, f"Instance '{instance_name}' deleted successfully")


def main() -> None:
    """
    Main entry point for instance delete command.
    """
    parser = argparse.ArgumentParser(
        description="Delete an OpenEdX instance and all associated resources"
    )
    parser.add_argument("instance_name", help="Name of the instance to delete")
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    setup_kubeconfig()

    try:
        delete_instance(args.instance_name, args.force)
    except subprocess.CalledProcessError as e:
        exit_with_error(logger, f"Command failed: {e}")
    except KubernetesError as e:
        exit_with_error(logger, f"Kubernetes error: {e}")
    except KeyboardInterrupt:
        exit_with_error(logger, "Instance deletion cancelled", exc_info=False)
    except Exception as e:  # pylint: disable=broad-exception-caught
        exit_with_error(logger, f"Unexpected error: {e}")
