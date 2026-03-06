"""
Argo user delete command.
"""

import argparse

from launchpad.cli.utils import exit_with_error, run_command_with_logging
from launchpad.exceptions import KubernetesError
from launchpad.kubeconfig import setup_kubeconfig
from launchpad.kubernetes import KubernetesClient
from launchpad.utils import get_logger, log_success

logger = get_logger(__name__)

ARGOCD_NAMESPACE = "argocd"


def _remove_rbac_policy(
    k8s_client: KubernetesClient,
    configmap_name: str,
    namespace: str,
    username: str,
) -> None:
    """
    Remove user from RBAC policy in a ConfigMap.

    Args:
        k8s_client: Kubernetes client
        configmap_name: Name of the ConfigMap containing RBAC policy
        namespace: Namespace of the ConfigMap
        username: Username to remove from policy
    """

    try:
        rbac_cm = run_command_with_logging(
            logger,
            f"read {configmap_name} RBAC config",
            k8s_client.read_config_map,
            name=configmap_name,
            namespace=namespace,
        )
        current_policy = rbac_cm.data.get("policy.csv", "")

        if current_policy:
            new_policy = "\n".join(
                [
                    line
                    for line in current_policy.split("\n")
                    if f"g, {username}, " not in line
                ]
            )

            if new_policy != current_policy:
                run_command_with_logging(
                    logger,
                    f"update {configmap_name} RBAC policy to remove user '{username}'",
                    k8s_client.patch_config_map,
                    name=configmap_name,
                    namespace=namespace,
                    data={"policy.csv": new_policy},
                )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Failed to update %s RBAC policy: %s", configmap_name, e)


def _remove_argocd_user(k8s_client: KubernetesClient, username: str) -> None:
    """
    Remove ArgoCD user from config and secret.

    Args:
        k8s_client: Kubernetes client
        username: Username to remove
    """

    logger.info("Removing ArgoCD user '%s'...", username)

    try:
        argocd_cm = run_command_with_logging(
            logger,
            "read ArgoCD config",
            k8s_client.read_config_map,
            name="argocd-cm",
            namespace=ARGOCD_NAMESPACE,
        )
        if argocd_cm.data and f"accounts.{username}" in argocd_cm.data:
            run_command_with_logging(
                logger,
                f"remove user '{username}' from ArgoCD config",
                k8s_client.patch_config_map,
                name="argocd-cm",
                namespace=ARGOCD_NAMESPACE,
                data={f"accounts.{username}": None},
            )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning(
            "Failed to remove user from argocd-cm: %s (user may not exist)", e
        )

    try:
        run_command_with_logging(
            logger,
            f"remove user '{username}' from ArgoCD secret",
            k8s_client.patch_secret,
            name="argocd-secret",
            namespace=ARGOCD_NAMESPACE,
            data={f"accounts.{username}.password": None},
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning(
            "Failed to remove user from argocd-secret: %s (user may not exist)", e
        )

    _remove_rbac_policy(k8s_client, "argocd-rbac-cm", ARGOCD_NAMESPACE, username)


def delete_argo_user(username: str, force: bool = False) -> None:
    """
    Delete an ArgoCD user and all associated resources.

    Args:
        username: Username to delete
        force: Skip confirmation prompt

    Raises:
        KubernetesError: If user deletion fails
    """

    logger.info("Starting deletion of user '%s' and all associated resources", username)
    logger.warning("This will permanently remove the user and all their permissions")

    if not force:
        confirm = input(f"Are you sure you want to delete user '{username}'? (y/N): ")
        if confirm.lower() not in ["y", "yes"]:
            logger.info("User deletion cancelled")
            return

    k8s_client = KubernetesClient()

    _remove_argocd_user(k8s_client, username)

    log_success(logger, f"User '{username}' deletion process completed")
    logger.warning("Restart the ArgoCD server to apply all changes:")
    logger.warning(
        "  kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-server"
    )


def main() -> None:
    """
    Main entry point for argo user delete command.
    """

    parser = argparse.ArgumentParser(
        description="Delete an ArgoCD user and all associated resources"
    )
    parser.add_argument("username", help="Username to delete")
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    setup_kubeconfig()

    try:
        delete_argo_user(args.username, args.force)
    except KubernetesError as e:
        exit_with_error(logger, f"Kubernetes error: {e}")
    except KeyboardInterrupt:
        exit_with_error(logger, "User deletion cancelled", exc_info=False)
    except Exception as e:  # pylint: disable=broad-exception-caught
        exit_with_error(logger, f"Unexpected error: {e}")
