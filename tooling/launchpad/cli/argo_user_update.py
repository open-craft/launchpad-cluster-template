"""
Argo user update command.
"""

import argparse

from launchpad.cli.utils import exit_with_error, run_command_with_logging
from launchpad.exceptions import KubernetesError
from launchpad.kubeconfig import setup_kubeconfig
from launchpad.kubernetes import KubernetesClient
from launchpad.utils import get_logger, log_success

logger = get_logger(__name__)

VALID_ROLES = ["admin", "developer", "readonly"]
DEFAULT_ROLE = "developer"
ARGOCD_NAMESPACE = "argocd"


def _update_rbac_policy(  # pylint: disable=duplicate-code
    k8s_client: KubernetesClient,
    configmap_name: str,
    namespace: str,
    username: str,
    role: str,
) -> None:
    """
    Update RBAC policy in a ConfigMap by adding/updating user role assignment.

    Args:
        k8s_client: Kubernetes client
        configmap_name: Name of the ConfigMap containing RBAC policy
        namespace: Namespace of the ConfigMap
        username: Username to add to policy
        role: Role to assign to user
    """

    config_map = run_command_with_logging(
        logger,
        f"read {configmap_name} RBAC config",
        k8s_client.read_config_map,
        name=configmap_name,
        namespace=namespace,
    )

    if config_map.data is None:
        config_map.data = {}

    policy_lines = [
        line
        for line in config_map.data.get("policy.csv", "").split("\n")
        if f"g, {username}, " not in line
    ]
    policy_lines.append(f"g, {username}, role:{role}")
    new_policy = "\n".join(policy_lines)

    run_command_with_logging(
        logger,
        f"update {configmap_name} RBAC policy for user '{username}'",
        k8s_client.patch_config_map,
        name=configmap_name,
        namespace=namespace,
        data={"policy.csv": new_policy},
    )


def update_argo_user_permissions(username: str, role: str = DEFAULT_ROLE) -> None:
    """
    Update ArgoCD user permissions to the specified role.

    Args:
        username: Username to update
        role: New user role (admin, developer, or readonly)

    Raises:
        KubernetesError: If permission update fails
        ValueError: If invalid role is provided
    """

    if role not in VALID_ROLES:
        raise ValueError(
            f"Invalid role '{role}'. Must be one of: {', '.join(VALID_ROLES)}"
        )

    logger.info("Updating permissions for user '%s' with role '%s'", username, role)

    k8s_client = KubernetesClient()

    _update_rbac_policy(
        k8s_client,
        "argocd-rbac-cm",
        ARGOCD_NAMESPACE,
        username,
        role,
    )

    log_success(logger, f"Permissions updated for user '{username}' with role '{role}'")
    logger.warning(
        "The user may need to log out and log back in for changes to take effect"
    )


def main() -> None:
    """
    Main entry point for argo user update command.
    """

    parser = argparse.ArgumentParser(
        description="Update ArgoCD user permissions to specified role"
    )
    parser.add_argument("username", help="Username to update")
    parser.add_argument(
        "--role",
        default=DEFAULT_ROLE,
        choices=VALID_ROLES,
        help=f"New user role (default: {DEFAULT_ROLE})",
    )

    args = parser.parse_args()

    setup_kubeconfig()

    try:
        update_argo_user_permissions(args.username, args.role)
    except ValueError as e:
        exit_with_error(logger, f"Validation error: {e}", exc_info=False)
    except KubernetesError as e:
        exit_with_error(logger, f"Kubernetes error: {e}")
    except KeyboardInterrupt:
        exit_with_error(logger, "Permission update cancelled", exc_info=False)
    except Exception as e:  # pylint: disable=broad-exception-caught
        exit_with_error(logger, f"Unexpected error: {e}")
