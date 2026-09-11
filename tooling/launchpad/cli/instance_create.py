"""
Instance create command.
"""

import argparse
import base64
import os
import subprocess
import tempfile
from pathlib import Path

from cookiecutter.main import cookiecutter

from launchpad.cli.argo_install import install_argo_workflows
from launchpad.cli.utils import (
    exit_with_error,
    run_command_with_logging,
    wait_for_workflow_completion,
)
from launchpad.config import get_config
from launchpad.exceptions import ConfigurationError, KubernetesError
from launchpad.git import (
    get_git_repo_branch,
    get_git_repo_url,
    parse_repo_name,
    parse_repo_owner,
)
from launchpad.kubeconfig import setup_kubeconfig
from launchpad.kubernetes import KubernetesClient
from launchpad.utils import (
    apply_generated_identity,
    build_instance_config,
    config_belongs_to_instance,
    copy_generated_application_if_missing,
    copy_instance_config_files,
    detect_local_template,
    get_logger,
    load_yaml,
    log_success,
    slugify,
    write_yaml,
)

logger = get_logger(__name__)

ARGO_NAMESPACE = "argo"
DEFAULT_PLATFORM_NAME = None
DEFAULT_TUTOR_VERSION = None
DEFAULT_EDX_PLATFORM_VERSION = None
DEFAULT_EDX_PLATFORM_REPOSITORY = None
DEFAULT_TEMPLATE_REPOSITORY = (
    "https://github.com/open-craft/launchpad-cluster-template.git"
)
DEFAULT_TEMPLATE_VERSION = None
LAUNCHPAD_MONGODB_USER_PASSWORD_SECRET = "launchpad-mongodb-user-password"


def _ensure_argo_workflows_installed() -> None:
    """
    Ensure Argo Workflows is installed before creating workflows.

    Raises:
        KubernetesError: If Argo Workflows installation fails
    """
    logger.info("Ensuring Argo Workflows is installed...")

    try:
        config = get_config()
        install_argo_workflows(config.cluster)
        logger.info("Argo Workflows is ready")
    except Exception as e:
        logger.error("Failed to ensure Argo Workflows is installed: %s", e)
        raise KubernetesError(f"Argo Workflows installation failed: {e}") from e


def _resolve_template_repository(template_repository: str | None) -> str:
    """
    Resolve a local instance-template path when the default GitHub URL is used.
    """

    if template_repository == DEFAULT_TEMPLATE_REPOSITORY:
        potential_local_template = detect_local_template("instance-template", logger)
        if potential_local_template:
            logger.info(
                "Detected local template repository, using: %s",
                potential_local_template,
            )
            template_repository = str(potential_local_template)

    if template_repository and template_repository.startswith((".", "/")):
        template_path = Path(template_repository).resolve()
        if template_path.is_dir():
            template_repository = str(template_path)
        elif template_path.name == "launchpad-cluster-template":
            instance_template_path = template_path / "instance-template"
            if instance_template_path.is_dir():
                template_repository = str(instance_template_path)

    return template_repository


def _build_cookiecutter_extra_context(  # pylint: disable=too-many-positional-arguments
    instance_name: str,
    template_repository: str | None,
    template_version: str | None,
    platform_name: str | None,
    edx_platform_repository: str | None,
    edx_platform_version: str | None,
    tutor_version: str | None,
) -> dict:
    """
    Build cookiecutter extra_context, including cluster repository metadata.
    """

    cluster_repo_url = get_git_repo_url()
    cluster_repo_branch = get_git_repo_branch()
    cluster_repo_owner = parse_repo_owner(cluster_repo_url)
    cluster_repo_name = parse_repo_name(cluster_repo_url)

    logger.info(
        "Detected cluster repository: url=%s, branch=%s, owner=%s, name=%s",
        cluster_repo_url or "",
        cluster_repo_branch or "",
        cluster_repo_owner or "",
        cluster_repo_name or "",
    )

    extra_context = {
        "instance_name": instance_name,
        "platform_repository": edx_platform_repository,
        "platform_name": platform_name,
        "platform_version": edx_platform_version,
        "tutor_version": tutor_version,
        "cluster_repository": cluster_repo_url,
        "cluster_repository_branch": cluster_repo_branch,
        "cluster_repository_owner": cluster_repo_owner,
        "cluster_repository_name": cluster_repo_name,
    }

    if template_repository:
        extra_context["template_repository"] = template_repository

    if template_version:
        extra_context["template_version"] = template_version

    return extra_context


def _run_cookiecutter(
    template_repository: str,
    template_version: str | None,
    extra_context: dict,
    output_dir: Path,
) -> None:
    """
    Render the instance template into output_dir.
    """

    cookiecutter_kwargs = {
        "checkout": template_version,
        "output_dir": str(output_dir),
        "overwrite_if_exists": False,
        "no_input": True,
        "extra_context": extra_context,
    }

    if not template_repository.startswith("/"):
        cookiecutter_kwargs["directory"] = "instance-template"

    run_command_with_logging(
        logger,
        "generate instance configuration",
        cookiecutter,
        template_repository,
        **cookiecutter_kwargs,
    )


def _render_instance_template(  # pylint: disable=too-many-positional-arguments
    output_dir: Path,
    instance_name: str,
    template_repository: str | None,
    template_version: str | None,
    platform_name: str | None,
    edx_platform_repository: str | None,
    edx_platform_version: str | None,
    tutor_version: str | None,
    cluster_domain: str,
    environment: str,
) -> None:
    """
    Resolve the template and cookiecutter-render an instance into output_dir.
    """

    template_repository = _resolve_template_repository(template_repository)
    logger.info(
        "Bootstrapping instance '%s' from template '%s'",
        instance_name,
        template_repository,
    )
    os.environ["LAUNCHPAD_CLUSTER_DOMAIN"] = cluster_domain
    os.environ["LAUNCHPAD_ENVIRONMENT"] = environment
    extra_context = _build_cookiecutter_extra_context(
        instance_name,
        template_repository,
        template_version,
        platform_name,
        edx_platform_repository,
        edx_platform_version,
        tutor_version,
    )
    _run_cookiecutter(template_repository, template_version, extra_context, output_dir)


def _cookiecutter_output_dir(output_dir: Path) -> Path:
    """
    Return the instance directory cookiecutter created under output_dir.
    """

    generated = [path for path in output_dir.iterdir() if path.is_dir()]
    if len(generated) != 1:
        raise FileNotFoundError(
            f"Expected one generated instance directory in {output_dir}, "
            f"found {len(generated)}"
        )
    return generated[0]


def _generate_instance_config(  # pylint: disable=too-many-positional-arguments,too-many-arguments,too-many-locals
    instance_name: str,
    template_repository: str | None,
    template_version: str | None,
    platform_name: str | None,
    edx_platform_repository: str | None,
    edx_platform_version: str | None,
    tutor_version: str | None,
    instances_dir: Path,
    cluster_domain: str,
    environment: str,
    *,
    from_instance: str | None = None,
) -> None:
    """
    Generate or reuse instance configuration.

    - Fresh create: cookiecutter into the instance directory
    - Retry / same-name migration: skip when dest config already belongs to this instance
    - Based on another instance: copy source files (optional) and rebase identity fields
    """

    dest_dir = instances_dir / instance_name
    dest_config = dest_dir / "config.yml"

    def render(output_dir: Path) -> None:
        _render_instance_template(
            output_dir,
            instance_name,
            template_repository,
            template_version,
            platform_name,
            edx_platform_repository,
            edx_platform_version,
            tutor_version,
            cluster_domain,
            environment,
        )

    def rebase() -> None:
        logger.info("Rebasing identity fields for instance '%s'", instance_name)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            render(tmp_path)
            apply_generated_identity(dest_dir, _cookiecutter_output_dir(tmp_path))

    if from_instance:
        if slugify(from_instance) == slugify(instance_name):
            raise ConfigurationError(
                "Cannot use --from-instance with the same instance name"
            )
        if dest_config.exists() and config_belongs_to_instance(
            load_yaml(dest_config), instance_name
        ):
            raise ConfigurationError(
                f"Instance '{instance_name}' already has matching configuration at "
                f"{dest_config}; refusing to overwrite with --from-instance"
            )
        source_config = instances_dir / from_instance / "config.yml"
        logger.info(
            "Copying instance configuration from %s into %s", source_config, dest_dir
        )
        copy_instance_config_files(source_config, dest_dir)
        rebase()
        log_success(
            logger,
            f"Instance '{instance_name}' configuration created from existing config",
        )
        return

    if dest_config.exists():
        if config_belongs_to_instance(load_yaml(dest_config), instance_name):
            dest_application = dest_dir / "application.yml"
            if dest_application.exists():
                logger.info(
                    "Instance '%s' configuration already exists at %s; "
                    "skipping generation",
                    instance_name,
                    dest_config,
                )
                return

            logger.info(
                "Instance '%s' configuration already exists at %s; "
                "generating missing application.yml",
                instance_name,
                dest_config,
            )

            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                render(tmp_path)
                copy_generated_application_if_missing(
                    dest_dir, _cookiecutter_output_dir(tmp_path)
                )

            log_success(
                logger,
                f"Instance '{instance_name}' application.yml generated from template",
            )

            return
        rebase()
        log_success(
            logger,
            f"Instance '{instance_name}' configuration rebased from existing config",
        )
        return

    if dest_dir.exists():
        raise FileNotFoundError(
            f"Instance directory exists but config.yml is missing: {dest_config}"
        )

    render(instances_dir)
    log_success(logger, f"Instance '{instance_name}' configuration generated")


def _setup_instance_rbac(
    k8s_client: KubernetesClient,
    instance_name: str,
    manifests_url: str,
) -> None:
    """
    Configure RBAC for instance namespace.

    Args:
        k8s_client: Kubernetes client
        instance_name: Name of the instance (used as namespace)
        manifests_url: Base URL for manifest files
    """

    run_command_with_logging(
        logger,
        f"configure instance RBAC for namespace '{instance_name}'",
        k8s_client.apply_manifest_from_url,
        f"{manifests_url}/openedx-instance-rbac.yml",
        instance_name,
        {"LAUNCHPAD_INSTANCE_NAME": instance_name},
    )

    log_success(logger, f"Instance RBAC configured for namespace '{instance_name}'")


def _provision_workflows(instance_name: str) -> list[tuple[str, str, str]]:
    """
    Return (type, manifest file, workflow name) for instance provision workflows.
    """

    return [
        (
            "MySQL",
            "launchpad-mysql-provision-workflow.yml",
            f"mysql-provision-{instance_name}",
        ),
        (
            "MongoDB",
            "launchpad-mongodb-provision-workflow.yml",
            f"mongodb-provision-{instance_name}",
        ),
        (
            "Storage",
            "launchpad-storage-provision-workflow.yml",
            f"storage-provision-{instance_name}",
        ),
    ]


def _delete_provision_workflows(instance_name: str) -> None:
    """
    Delete existing provision workflows so a retry can re-run them.
    """

    for _, _, workflow_name in _provision_workflows(instance_name):
        subprocess.run(
            [
                "kubectl",
                "delete",
                "workflow",
                workflow_name,
                "-n",
                instance_name,
                "--ignore-not-found=true",
            ],
            check=False,
            capture_output=True,
        )


def _create_provision_workflows(  # pylint: disable=duplicate-code
    k8s_client: KubernetesClient,
    instance_name: str,
    manifests_url: str,
    instance_config: dict,
) -> None:
    """
    Create and execute provision workflows for MySQL, MongoDB, and Storage.

    Args:
        k8s_client: Kubernetes client
        instance_name: Name of the instance
        manifests_url: Base URL for manifest files
        instance_config: Configuration dictionary for the instance

    Raises:
        KubernetesError: If workflows fail
    """

    logger.info("Creating parameterized workflows for instance '%s'", instance_name)

    workflows = _provision_workflows(instance_name)

    logger.info("Deleting existing provision workflows if present...")
    _delete_provision_workflows(instance_name)

    for workflow_type, manifest_file, _workflow_name in workflows:
        run_command_with_logging(
            logger,
            f"apply {workflow_type} provision workflow",
            k8s_client.apply_manifest_from_url,
            f"{manifests_url}/{manifest_file}",
            instance_name,
            instance_config,
        )

    logger.info("Waiting for provision workflows to complete...")
    all_succeeded = True

    for workflow_type, _, workflow_name in workflows:
        if not wait_for_workflow_completion(
            instance_name, workflow_name, logger=logger
        ):
            all_succeeded = False

    subprocess.run(
        ["kubectl", "get", "workflows", "-n", instance_name],
        check=False,
    )

    if not all_succeeded:
        raise KubernetesError(
            f"Workflows may have failed for instance '{instance_name}'"
        )

    logger.warning("Cleaning up workflows to save resources...")
    _delete_provision_workflows(instance_name)

    log_success(
        logger,
        f"Workflows created and completed successfully for instance '{instance_name}'",
    )


def _create_argocd_application(instance_name: str, instances_dir: Path) -> None:
    """
    Create ArgoCD Application for the instance.

    Args:
        instance_name: Name of the instance
        instances_dir: Directory where instances are stored

    Raises:
        FileNotFoundError: If application.yml not found
        subprocess.CalledProcessError: If kubectl apply fails
    """

    logger.info("Creating ArgoCD Application for instance '%s'", instance_name)

    application_file = instances_dir / instance_name / "application.yml"

    if not application_file.exists():
        raise FileNotFoundError(
            f"ArgoCD Application file not found: {application_file}"
        )

    run_command_with_logging(
        logger,
        f"create ArgoCD Application for instance '{instance_name}'",
        subprocess.run,
        ["kubectl", "apply", "-f", str(application_file)],
        check=True,
    )

    log_success(
        logger,
        f"ArgoCD Application created successfully for instance '{instance_name}'",
    )


def _update_mongodb_password(
    instance_name: str,
    config_data: dict,
    config_file: Path,
    k8s_client: KubernetesClient,
):
    """
    Update MongoDB password in the instance config.

    Fetches the password from the k8s secret created by the provisioning workflow.
    Updates the MongoDB password in the config file.
    Deletes the secret.

    Args:
        instance_name (str): The instance name
        config_data (dict): Existing config data
        config_file (Path): Instance config file to update
        k8s_client (KubernetesClient): Kubernetes client
    """
    try:
        mongodb_password_data = k8s_client.read_secret(
            LAUNCHPAD_MONGODB_USER_PASSWORD_SECRET, instance_name
        ).data
        mongodb_password = base64.b64decode(
            mongodb_password_data[LAUNCHPAD_MONGODB_USER_PASSWORD_SECRET]
        ).decode("utf-8")
        config_data["MONGODB_PASSWORD"] = mongodb_password
        write_yaml(config_file, config_data)
        k8s_client.delete_secret(LAUNCHPAD_MONGODB_USER_PASSWORD_SECRET, instance_name)
    except KubernetesError as e:
        logger.info(
            "Failed to read secret %s for namespace %s: %s",
            LAUNCHPAD_MONGODB_USER_PASSWORD_SECRET,
            instance_name,
            e,
        )


def create_instance(  # pylint: disable=too-many-positional-arguments,too-many-locals
    instance_name: str,
    template_repository: str | None = DEFAULT_TEMPLATE_REPOSITORY,
    template_version: str | None = DEFAULT_TEMPLATE_VERSION,
    platform_name: str | None = DEFAULT_PLATFORM_NAME,
    edx_platform_repository: str | None = DEFAULT_EDX_PLATFORM_REPOSITORY,
    edx_platform_version: str | None = DEFAULT_EDX_PLATFORM_VERSION,
    tutor_version: str | None = DEFAULT_TUTOR_VERSION,
    *,
    from_instance: str | None = None,
) -> None:
    """
    Create a new OpenEdX instance with all required resources.

    This orchestrates:
    - Generating instance configuration from template, or reusing/cloning existing config
    - Creating namespace
    - Setting up RBAC
    - Running provision workflows
    - Creating ArgoCD application

    Args:
        instance_name: Name of the instance to create
        template_repository: Git URL of the instance template repository
        template_version: Version of the instance template to use
        platform_name: Display name for the platform
        edx_platform_repository: Git URL of the edx-platform repository
        edx_platform_version: Version/branch of edx-platform to use
        tutor_version: Version of Tutor to use
        from_instance: Existing instance name whose config to clone

    Raises:
        KubernetesError: If instance creation fails
        FileNotFoundError: If required files not found
        subprocess.CalledProcessError: If external commands fail
    """

    config = get_config()
    k8s_client = KubernetesClient()
    instances_dir = Path(
        # pylint: disable=no-member
        config.cluster.instances_directory
    )

    instances_dir.mkdir(parents=True, exist_ok=True)

    _generate_instance_config(
        instance_name,
        template_repository,
        template_version,
        platform_name,
        edx_platform_repository,
        edx_platform_version,
        tutor_version,
        instances_dir,
        config.cluster.cluster_domain,  # pylint: disable=no-member
        config.cluster.environment,  # pylint: disable=no-member
        from_instance=from_instance,
    )

    run_command_with_logging(
        logger,
        f"create namespace '{instance_name}'",
        k8s_client.create_namespace,
        instance_name,
    )

    manifests_url = config.cluster.opencraft_manifests_url  # pylint: disable=no-member

    _setup_instance_rbac(k8s_client, instance_name, manifests_url)
    _ensure_argo_workflows_installed()

    config_file = instances_dir / instance_name / "config.yml"
    if not config_file.exists():
        raise FileNotFoundError(f"Instance config file not found: {config_file}")

    config_data = load_yaml(config_file)

    instance_config = build_instance_config(
        instance_name,
        config_data,
        k8s_api_bearer_token=k8s_client.get_api_bearer_token(),
        platform_name=platform_name,
        edx_platform_repository=edx_platform_repository,
        edx_platform_version=edx_platform_version,
        tutor_version=tutor_version,
    )

    _create_provision_workflows(
        k8s_client, instance_name, manifests_url, instance_config
    )

    _update_mongodb_password(instance_name, config_data, config_file, k8s_client)

    _create_argocd_application(instance_name, instances_dir)

    log_success(logger, f"Instance '{instance_name}' created successfully")


def main() -> None:
    """
    Main entry point for instance create command.
    """

    parser = argparse.ArgumentParser(description="Create a new OpenEdX instance")
    parser.add_argument("instance_name", help="Name of the instance to create")
    parser.add_argument(
        "--template-repository",
        default=DEFAULT_TEMPLATE_REPOSITORY,
        help=f"Git URL of the instance template repository (default: {DEFAULT_TEMPLATE_REPOSITORY})",
    )
    parser.add_argument(
        "--template-version",
        default=DEFAULT_TEMPLATE_VERSION,
        help=f"Version of the instance template to use (default: {DEFAULT_TEMPLATE_VERSION})",
    )
    parser.add_argument(
        "--platform-name",
        default="My Open edX Instance",
        help="Display name for the platform (default: 'My Open edX Instance')",
    )
    parser.add_argument(
        "--edx-platform-repository",
        default=DEFAULT_EDX_PLATFORM_REPOSITORY,
        help=f"Git URL of the edx-platform repository (default: {DEFAULT_EDX_PLATFORM_REPOSITORY})",
    )
    parser.add_argument(
        "--edx-platform-version",
        default=DEFAULT_EDX_PLATFORM_VERSION,
        help=f"Version/branch of edx-platform to use (default: {DEFAULT_EDX_PLATFORM_VERSION})",
    )
    parser.add_argument(
        "--tutor-version",
        default=DEFAULT_TUTOR_VERSION,
        help=f"Version of Tutor to use (default: {DEFAULT_TUTOR_VERSION})",
    )
    parser.add_argument(
        "--from-instance",
        default=None,
        help="Clone config.yml and application.yml from an existing instance, then rewrite identity and credentials",
    )

    args = parser.parse_args()

    setup_kubeconfig()

    try:
        create_instance(
            instance_name=args.instance_name,
            template_repository=args.template_repository,
            template_version=args.template_version,
            platform_name=args.platform_name,
            edx_platform_repository=args.edx_platform_repository,
            edx_platform_version=args.edx_platform_version,
            tutor_version=args.tutor_version,
            from_instance=args.from_instance,
        )
    except FileNotFoundError as e:
        exit_with_error(logger, f"File not found: {e}", exc_info=False)
    except ConfigurationError as e:
        exit_with_error(logger, f"Configuration error: {e}", exc_info=False)
    except subprocess.CalledProcessError as e:
        exit_with_error(logger, f"Command failed: {e}")
    except KubernetesError as e:
        exit_with_error(logger, f"Kubernetes error: {e}")
    except KeyboardInterrupt:
        exit_with_error(logger, "Instance creation cancelled", exc_info=False)
    except Exception as e:  # pylint: disable=broad-exception-caught
        exit_with_error(logger, f"Unexpected error: {e}")
