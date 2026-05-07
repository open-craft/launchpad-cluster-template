"""
Tests for MySQL deprovision manifests.
"""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MYSQL_DEPROVISION_WORKFLOW = (
    REPO_ROOT / "manifests" / "launchpad-mysql-deprovision-workflow.yml"
)
MYSQL_DEPROVISION_TEMPLATE = (
    REPO_ROOT / "manifests" / "launchpad-mysql-deprovision-template.yml"
)


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as file_obj:
        return yaml.safe_load(file_obj)


def _parameter_names(document: dict) -> set[str]:
    return {param["name"] for param in document["spec"]["arguments"]["parameters"]}


def _template_map(document: dict) -> dict:
    return {template["name"]: template for template in document["spec"]["templates"]}


class TestMySQLDeprovisionWorkflowManifest:
    """
    Tests for launchpad-mysql-deprovision-workflow.yml.
    """

    def test_wires_provider_specific_parameters(self):
        """
        Test that workflow manifest wires provider-specific MySQL parameters.
        """
        manifest = _load_yaml(MYSQL_DEPROVISION_WORKFLOW)
        parameters = {
            param["name"]: param.get("value")
            for param in manifest["spec"]["arguments"]["parameters"]
        }

        assert parameters["mysql-provider"] == "{{ LAUNCHPAD_INSTANCE_MYSQL_PROVIDER }}"
        assert (
            parameters["mysql-cluster-id"]
            == "{{ LAUNCHPAD_INSTANCE_MYSQL_CLUSTER_ID }}"
        )
        assert (
            parameters["digitalocean-token"]
            == "{{ LAUNCHPAD_INSTANCE_DIGITALOCEAN_TOKEN }}"
        )

    def test_workflow_and_template_parameter_sets_match(self):
        """
        Test workflow parameter names and template parameter names stay in sync.
        """
        workflow = _load_yaml(MYSQL_DEPROVISION_WORKFLOW)
        template = _load_yaml(MYSQL_DEPROVISION_TEMPLATE)

        assert _parameter_names(workflow) == _parameter_names(template)


class TestMySQLDeprovisionTemplateManifest:
    """
    Tests for launchpad-mysql-deprovision-template.yml.
    """

    def test_main_template_routes_by_provider(self):
        """
        Test that main workflow routes deprovision logic by provider.
        """
        manifest = _load_yaml(MYSQL_DEPROVISION_TEMPLATE)
        templates = _template_map(manifest)

        main_steps = templates["main"]["steps"]
        flattened_steps = [step for step_group in main_steps for step in step_group]
        step_names = {step["name"] for step in flattened_steps}

        assert "validate-provider" in step_names
        assert "deprovision-direct-sql" in step_names
        assert "deprovision-digitalocean" in step_names

        direct_sql_step = next(
            step for step in flattened_steps if step["name"] == "deprovision-direct-sql"
        )
        digitalocean_step = next(
            step
            for step in flattened_steps
            if step["name"] == "deprovision-digitalocean"
        )

        assert (
            direct_sql_step["when"]
            == "{{workflow.parameters.mysql-provider}} == 'direct_sql'"
        )
        assert (
            digitalocean_step["when"]
            == "{{workflow.parameters.mysql-provider}} == 'digitalocean_api'"
        )

    def test_direct_sql_template_verifies_database_and_all_user_hosts(self):
        """
        Test direct SQL deprovision script includes post-delete verification.
        """
        manifest = _load_yaml(MYSQL_DEPROVISION_TEMPLATE)
        templates = _template_map(manifest)
        script_source = templates["deprovision-direct-sql"]["script"]["source"]

        assert "REMAINING_DATABASES" in script_source
        assert "REMAINING_USERS" in script_source

    def test_digitalocean_template_verifies_api_delete_outcome(self):
        """
        Test DigitalOcean deprovision script checks API status and verifies absence.
        """
        manifest = _load_yaml(MYSQL_DEPROVISION_TEMPLATE)
        templates = _template_map(manifest)
        script_source = templates["deprovision-digitalocean-api"]["script"]["source"]

        assert "delete_resource" in script_source
        assert "204|404)" in script_source
        assert "verify_resource_absent" in script_source

    def test_provider_routes_match_validate_provider_guard(self):
        """
        Test providers listed in route conditions are covered by provider validation.
        """
        manifest = _load_yaml(MYSQL_DEPROVISION_TEMPLATE)
        templates = _template_map(manifest)

        main_steps = templates["main"]["steps"]
        routed_steps = [
            step
            for step_group in main_steps
            for step in step_group
            if "when" in step and "mysql-provider" in step["when"]
        ]
        providers_in_routes = {
            match.group(1)
            for step in routed_steps
            for match in [
                re.search(r"== '([^']+)'", step["when"]),
            ]
            if match is not None
        }

        validate_provider_script = templates["validate-provider"]["script"]["source"]
        for provider in providers_in_routes:
            assert provider in validate_provider_script
