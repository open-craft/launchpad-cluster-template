"""
Cluster create command.
"""

import argparse
from pathlib import Path

from cookiecutter.main import cookiecutter

from launchpad.cli.utils import exit_with_error
from launchpad.utils import detect_local_template, get_logger, log_success

logger = get_logger(__name__)

DEFAULT_ENVIRONMENT = "production"
DEFAULT_SHORT_DESCRIPTION = "Kubernetes cluster to host Open edX instances"
DEFAULT_CLOUD_PROVIDER = None
DEFAULT_CLOUD_REGION = None
DEFAULT_HARMONY_MODULE_VERSION = None
DEFAULT_OPENCRAFT_MODULE_VERSION = None
DEFAULT_PICASSO_VERSION = None
DEFAULT_TEMPLATE_VERSION = None
DEFAULT_TUTOR_VERSION = None
DEFAULT_GITHUB_ORGANIZATION = None
DEFAULT_TEMPLATE_REPOSITORY = (
    "https://github.com/open-craft/launchpad-cluster-template.git"
)


def create_cluster(  # pylint: disable=too-many-branches,too-many-arguments,too-many-positional-arguments,too-many-locals
    cluster_name: str,
    cluster_domain: str,
    environment: str = DEFAULT_ENVIRONMENT,
    short_description: str = DEFAULT_SHORT_DESCRIPTION,
    cloud_provider: str | None = DEFAULT_CLOUD_PROVIDER,
    cloud_region: str | None = DEFAULT_CLOUD_REGION,
    harmony_module_version: str | None = DEFAULT_HARMONY_MODULE_VERSION,
    opencraft_module_version: str | None = DEFAULT_OPENCRAFT_MODULE_VERSION,
    picasso_version: str | None = DEFAULT_PICASSO_VERSION,
    template_version: str | None = DEFAULT_TEMPLATE_VERSION,
    tutor_version: str | None = DEFAULT_TUTOR_VERSION,
    github_organization: str | None = DEFAULT_GITHUB_ORGANIZATION,
    github_repository: str | None = None,
    template_repository: str = DEFAULT_TEMPLATE_REPOSITORY,
    output_dir: str = ".",
) -> None:
    """
    Create a new cluster configuration using cookiecutter.

    Args:
        cluster_name: Name of the cluster (e.g., "Launchpad Production Cluster")
        cluster_domain: Domain for the cluster (e.g., "cluster.cluster.domain")
        environment: Environment name (default: "production")
        short_description: Short description of the cluster
        cloud_provider: Cloud provider (aws or digitalocean)
        cloud_region: Region of the chosen cloud provider
        harmony_module_version: Harmony module version/commit hash
        opencraft_module_version: OpenCraft module version
        picasso_version: Picasso version
        template_version: Launchpad cluster template version
        tutor_version: Tutor version
        github_organization: Git organization name
        github_repository: Git repository URL (if not provided, will be auto-generated)
        template_repository: Git URL of the cluster template repository
        output_dir: Directory where cluster config will be created

    Raises:
        Exception: If cookiecutter fails
    """

    logger.info("Creating cluster configuration for '%s'", cluster_name)

    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    # Detect local template if using default GitHub repository
    if template_repository == DEFAULT_TEMPLATE_REPOSITORY:
        potential_local_template = detect_local_template("cluster-template", logger)
        if potential_local_template:
            logger.info(
                "Detected local template repository, using: %s",
                potential_local_template,
            )
            template_repository = str(potential_local_template)

    # Use absolute path for local templates
    if template_repository.startswith((".", "/")):
        template_path = Path(template_repository).resolve()
        if template_path.is_dir():
            template_repository = str(template_path)
        elif template_path.name == "launchpad-cluster-template":
            cluster_template_path = template_path / "cluster-template"
            if cluster_template_path.is_dir():
                template_repository = str(cluster_template_path)

    logger.info("generate cluster configuration")
    logger.info("Using template repository: %s", template_repository)

    extra_context = {
        "environment": environment,
        "cluster_name": cluster_name,
        "cluster_domain": cluster_domain,
        "short_description": short_description,
    }

    if cloud_provider:
        extra_context["cloud_provider"] = [cloud_provider]

    if cloud_region:
        extra_context["cloud_region"] = [cloud_region]

    if harmony_module_version:
        extra_context["harmony_module_version"] = harmony_module_version

    if opencraft_module_version:
        extra_context["opencraft_module_version"] = opencraft_module_version

    if picasso_version:
        extra_context["picasso_version"] = picasso_version

    if template_version:
        extra_context["launchpad_cluster_template_version"] = template_version

    if tutor_version:
        extra_context["tutor_version"] = tutor_version

    if github_organization:
        extra_context["github_organization"] = github_organization

    if github_repository:
        extra_context["github_repository"] = github_repository

    logger.debug("Template repository: %s", template_repository)
    logger.debug("Extra context: %s", extra_context)

    cookiecutter_kwargs = {
        "checkout": template_version,
        "output_dir": str(output_path),
        "overwrite_if_exists": False,
        "no_input": True,
        "extra_context": extra_context,
    }

    if not template_repository.startswith("/"):
        cookiecutter_kwargs["directory"] = "cluster-template"

    try:
        cookiecutter(template_repository, **cookiecutter_kwargs)
    except Exception as e:
        logger.error("Failed to generate cluster configuration: %s", e)
        raise

    log_success(
        logger, f"Cluster configuration created successfully for '{cluster_name}'"
    )


def main() -> None:
    """
    Main entry point for cluster create command.
    """

    parser = argparse.ArgumentParser(description="Create a new cluster configuration")
    parser.add_argument(
        "cluster_name",
        help="Name of the cluster (e.g., 'Launchpad Production Cluster')",
    )
    parser.add_argument(
        "cluster_domain", help="Domain for the cluster (e.g., 'cluster.cluster.domain')"
    )
    parser.add_argument(
        "--environment",
        default=DEFAULT_ENVIRONMENT,
        help=f"Environment name (default: {DEFAULT_ENVIRONMENT})",
    )
    parser.add_argument(
        "--short-description",
        default=DEFAULT_SHORT_DESCRIPTION,
        help=f"Short description of the cluster (default: '{DEFAULT_SHORT_DESCRIPTION}')",
    )
    parser.add_argument(
        "--cloud-provider",
        default=DEFAULT_CLOUD_PROVIDER,
        choices=["aws", "digitalocean"],
        help=f"Cloud provider (default: {DEFAULT_CLOUD_PROVIDER})",
    )
    parser.add_argument(
        "--cloud-region",
        default=DEFAULT_CLOUD_REGION,
        help=f"Cloud provider region (default: {DEFAULT_CLOUD_REGION})",
    )
    parser.add_argument(
        "--harmony-module-version",
        default=DEFAULT_HARMONY_MODULE_VERSION,
        help=f"Harmony module version/commit hash (default: {DEFAULT_HARMONY_MODULE_VERSION})",
    )
    parser.add_argument(
        "--opencraft-module-version",
        default=DEFAULT_OPENCRAFT_MODULE_VERSION,
        help=f"OpenCraft module version (default: {DEFAULT_OPENCRAFT_MODULE_VERSION})",
    )
    parser.add_argument(
        "--picasso-version",
        default=DEFAULT_PICASSO_VERSION,
        help=f"Picasso version (default: {DEFAULT_PICASSO_VERSION})",
    )
    parser.add_argument(
        "--template-version",
        default=DEFAULT_TEMPLATE_VERSION,
        help=f"Launchpad cluster template version (default: {DEFAULT_TEMPLATE_VERSION})",
    )
    parser.add_argument(
        "--tutor-version",
        default=DEFAULT_TUTOR_VERSION,
        help=f"Tutor version (default: {DEFAULT_TUTOR_VERSION})",
    )
    parser.add_argument(
        "--github-organization",
        default=DEFAULT_GITHUB_ORGANIZATION,
        help=f"GitHub organization name (default: {DEFAULT_GITHUB_ORGANIZATION})",
    )
    parser.add_argument(
        "--github-repository",
        default="",
        help="GitHub repository URL (if not provided, will be auto-generated)",
    )
    parser.add_argument(
        "--template-repository",
        default=DEFAULT_TEMPLATE_REPOSITORY,
        help=f"GitHub URL of the cluster template repository (default: {DEFAULT_TEMPLATE_REPOSITORY})",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where cluster config will be created (default: current directory)",
    )

    args = parser.parse_args()

    try:
        create_cluster(
            args.cluster_name,
            args.cluster_domain,
            args.environment,
            args.short_description,
            args.cloud_provider,
            args.cloud_region,
            args.harmony_module_version,
            args.opencraft_module_version,
            args.picasso_version,
            args.template_version,
            args.tutor_version,
            args.github_organization,
            args.github_repository,
            args.template_repository,
            args.output_dir,
        )
    except KeyboardInterrupt:
        exit_with_error(logger, "Cluster creation cancelled", exc_info=False)
    except Exception as e:  # pylint: disable=broad-exception-caught
        exit_with_error(logger, f"Unexpected error: {e}")
