"""
Argo user create command.
"""

import argparse
import base64
import getpass

from launchpad.cli.utils import exit_with_error, run_command_with_logging
from launchpad.exceptions import KubernetesError
from launchpad.kubeconfig import setup_kubeconfig
from launchpad.kubernetes import KubernetesClient
from launchpad.password import bcrypt_password
from launchpad.utils import (
    get_logger,
    log_success,
    sanitize_username,
)

logger = get_logger(__name__)

VALID_ROLES = ["admin", "developer", "readonly"]
DEFAULT_ROLE = "developer"
ARGOCD_NAMESPACE = "argocd"


def _prompt_for_password(username: str) -> str:
    """
    Prompt user for password with confirmation.

    Args:
        username: Username for context in the prompt

    Returns:
        The validated password

    Raises:
        ValueError: If passwords don't match or password is empty
    """

    logger.info("Enter a password for %s:", username)
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm password: ")

    if password != password_confirm:
        raise ValueError("Passwords do not match")

    if not password:
        raise ValueError("Password cannot be empty")

    return password


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


def _configure_argocd_user(
    k8s_client: KubernetesClient,
    username: str,
    role: str,
    password_hash: str,
) -> None:
    """
    Configure ArgoCD user with account and RBAC.

    Args:
        k8s_client: Kubernetes client
        username: Username to configure
        role: Role to assign
        password_hash: Bcrypt password hash
    """

    logger.info("Configuring ArgoCD user '%s'", username)

    sanitized_username = sanitize_username(username)

    argocd_cm = run_command_with_logging(
        logger,
        "read ArgoCD config",
        k8s_client.read_config_map,
        name="argocd-cm",
        namespace=ARGOCD_NAMESPACE,
    )
    if argocd_cm.data is None:
        argocd_cm.data = {}

    argocd_cm.data[f"accounts.{sanitized_username}"] = "login"

    run_command_with_logging(
        logger,
        f"update ArgoCD config for user '{username}'",
        k8s_client.patch_config_map,
        name="argocd-cm",
        namespace=ARGOCD_NAMESPACE,
        data=argocd_cm.data,
    )

    hash_b64 = base64.b64encode(password_hash.encode("utf-8")).decode("utf-8")
    run_command_with_logging(
        logger,
        f"update ArgoCD secret for user '{username}'",
        k8s_client.patch_secret,
        name="argocd-secret",
        namespace=ARGOCD_NAMESPACE,
        data={f"accounts.{sanitized_username}.password": hash_b64},
    )

    _update_rbac_policy(
        k8s_client,
        "argocd-rbac-cm",
        ARGOCD_NAMESPACE,
        sanitized_username,
        role,
    )

    log_success(logger, f"ArgoCD user '{username}' configured with role '{role}'")
    logger.warning("Restart the argocd-server pod to apply login changes:")
    logger.warning(
        "  kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-server"
    )


def create_argo_user(
    username: str, role: str = DEFAULT_ROLE, password: str = ""
) -> None:
    """
    Create an ArgoCD user with the specified role and password.

    Args:
        username: Username to create
        role: User role (admin, developer, or readonly)
        password: User password (will prompt if not provided)

    Raises:
        KubernetesError: If user creation fails
        ValueError: If invalid role is provided or password validation fails
    """

    if role not in VALID_ROLES:
        raise ValueError(
            f"Invalid role '{role}'. Must be one of: {', '.join(VALID_ROLES)}"
        )

    if not password:
        password = _prompt_for_password(username)

    logger.info("Creating user '%s' with role '%s'", username, role)

    k8s_client = KubernetesClient()
    password_hash = bcrypt_password(password)

    _configure_argocd_user(k8s_client, username, role, password_hash)

    log_success(
        logger,
        f"ArgoCD user '{username}' created successfully with role '{role}'",
    )


def main() -> None:
    """
    Main entry point for argo user create command.
    """

    parser = argparse.ArgumentParser(
        description="Create an Argo user with specified role and password"
    )
    parser.add_argument("username", help="Username to create")
    parser.add_argument(
        "--role",
        default=DEFAULT_ROLE,
        choices=VALID_ROLES,
        help=f"User role (default: {DEFAULT_ROLE})",
    )
    parser.add_argument(
        "--password", default="", help="User password (will prompt if not provided)"
    )

    args = parser.parse_args()

    setup_kubeconfig()

    try:
        create_argo_user(args.username, args.role, args.password)
    except ValueError as e:
        exit_with_error(logger, f"Validation error: {e}", exc_info=False)
    except KubernetesError as e:
        exit_with_error(logger, f"Kubernetes error: {e}")
    except KeyboardInterrupt:
        exit_with_error(logger, "User creation cancelled", exc_info=False)
    except Exception as e:  # pylint: disable=broad-exception-caught
        exit_with_error(logger, f"Unexpected error: {e}")
