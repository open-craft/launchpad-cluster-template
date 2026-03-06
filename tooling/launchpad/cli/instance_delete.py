"""
Instance delete command.
"""

import argparse
import subprocess
from pathlib import Path

from launchpad.cli.utils import exit_with_error, run_command_with_logging
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

WORKFLOW_TIMEOUT = 300


def _wait_for_workflow_completion(  # pylint: disable=duplicate-code
    instance_name: str,
    workflow_name: str,
    timeout: int = WORKFLOW_TIMEOUT,
) -> bool:
    """
    Wait for an Argo Workflow to complete and check its status.

    Args:
        instance_name: Namespace where the workflow runs
        workflow_name: Name of the workflow to wait for
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
    all_succeeded = True

    for workflow_type, _, workflow_name in workflows:
        if not _wait_for_workflow_completion(instance_name, workflow_name):
            all_succeeded = False

    subprocess.run(
        ["kubectl", "get", "workflows", "-n", instance_name],
        check=False,
    )

    if all_succeeded:
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

        try:
            subprocess.run(
                ["kubectl", "delete", "namespace", instance_name, "--timeout=300s"],
                check=True,
                capture_output=False,
            )
        except subprocess.CalledProcessError as exc:
            logger.warning(
                "Failed to delete namespace (some resources may still be terminating)"
            )
            raise KubernetesError(
                f"Failed to delete namespace '{instance_name}'"
            ) from exc

        result = subprocess.run(
            ["kubectl", "get", "namespace", instance_name],
            capture_output=True,
            check=False,
        )

        if result.returncode == 0:
            logger.warning("Namespace '%s' still exists", instance_name)
            subprocess.run(["kubectl", "get", "namespace", instance_name], check=False)
            raise KubernetesError(f"Namespace '{instance_name}' was not fully deleted")

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
