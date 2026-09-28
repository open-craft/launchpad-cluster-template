"""
Tests for MongoDB provision manifests.
"""

from pathlib import Path

from launchpad.utils import load_yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MONGODB_PROVISION_WORKFLOW = (
    REPO_ROOT / "manifests" / "launchpad-mongodb-provision-workflow.yml"
)
MONGODB_PROVISION_TEMPLATE = (
    REPO_ROOT / "manifests" / "launchpad-mongodb-provision-template.yml"
)


def _parameter_names(document: dict) -> set[str]:
    return {param["name"] for param in document["spec"]["arguments"]["parameters"]}


def _template_map(document: dict) -> dict:
    return {template["name"]: template for template in document["spec"]["templates"]}


def _command_block(script_source: str, command: str) -> str:
    """
    Return one continued shell command containing the named executable.
    """
    lines = script_source.splitlines()
    for index, line in enumerate(lines):
        if command not in line:
            continue
        collected = [line]
        while collected[-1].rstrip().endswith("\\"):
            index += 1
            collected.append(lines[index])
        return "\n".join(collected)
    raise AssertionError(f"Command not found: {command}")


class TestMongoDBProvisionWorkflowManifest:
    """
    Tests for launchpad-mongodb-provision-workflow.yml.
    """

    def test_wires_forum_database_and_provider(self):
        """
        Test that the workflow passes the forum database and Atlas provider inputs.
        """
        manifest = load_yaml(MONGODB_PROVISION_WORKFLOW)
        parameters = {
            param["name"]: param.get("value")
            for param in manifest["spec"]["arguments"]["parameters"]
        }

        assert (
            parameters["forum-database-name"]
            == "{{ LAUNCHPAD_INSTANCE_MONGODB_DATABASE_FORUM }}"
        )
        assert (
            parameters["mongodb-provider"]
            == "{{ LAUNCHPAD_INSTANCE_MONGODB_PROVIDER }}"
        )
        assert (
            parameters["atlas-project-id"]
            == "{{ LAUNCHPAD_INSTANCE_ATLAS_PROJECT_ID }}"
        )
        assert (
            parameters["atlas-cluster-name"]
            == "{{ LAUNCHPAD_INSTANCE_ATLAS_CLUSTER_NAME }}"
        )

    def test_workflow_and_template_parameter_sets_match(self):
        """
        Test workflow parameter names and template parameter names stay in sync.
        """
        workflow = load_yaml(MONGODB_PROVISION_WORKFLOW)
        template = load_yaml(MONGODB_PROVISION_TEMPLATE)

        assert _parameter_names(workflow) == _parameter_names(template)


class TestMongoDBProvisionTemplateManifest:
    """
    Tests for launchpad-mongodb-provision-template.yml.
    """

    def test_main_template_routes_by_provider(self):
        """
        Test that the main workflow routes provision logic by provider.
        """
        manifest = load_yaml(MONGODB_PROVISION_TEMPLATE)
        templates = _template_map(manifest)

        main_steps = templates["main"]["steps"]
        flattened_steps = [step for step_group in main_steps for step in step_group]
        routed_steps = {
            step["name"]: step["when"]
            for step in flattened_steps
            if "when" in step and "mongodb-provider" in step["when"]
        }

        assert (
            routed_steps["provision-digitalocean"]
            == "{{workflow.parameters.mongodb-provider}} == 'digitalocean_api'"
        )
        assert (
            routed_steps["provision-atlas"]
            == "{{workflow.parameters.mongodb-provider}} == 'atlas'"
        )

    def test_digitalocean_user_receives_both_databases(self):
        """
        Test DigitalOcean user creation grants readWrite on both databases.
        """
        manifest = load_yaml(MONGODB_PROVISION_TEMPLATE)
        script_source = _template_map(manifest)["create-user-digitalocean"]["script"][
            "source"
        ]

        assert "FORUM_DATABASE_NAME" in script_source
        assert (
            r"\"databases\": [\"$DATABASE_NAME\", \"$FORUM_DATABASE_NAME\"]"
            in script_source
        )
        assert r"\"role\": \"readWrite\"" in script_source

    def test_atlas_user_receives_both_databases_on_create_and_update(self):
        """
        Test Atlas create and update both grant readWrite on the forum database.
        """
        manifest = load_yaml(MONGODB_PROVISION_TEMPLATE)
        script_source = _template_map(manifest)["create-user-atlas"]["script"]["source"]

        assert 'FORUM_DATABASE_NAME="{{workflow.parameters.forum-database-name}}"' in (
            script_source
        )
        assert 'ROLES="readWrite@${DATABASE_NAME}"' in script_source
        assert 'ROLES="${ROLES},readWrite@${FORUM_DATABASE_NAME}"' in script_source

        create_command = _command_block(script_source, "atlas dbusers create")
        update_command = _command_block(script_source, "atlas dbusers update")

        assert '--role "$ROLES"' in create_command
        assert '--role "$ROLES"' in update_command
        assert "readWrite@$DATABASE_NAME" not in create_command
        assert "readWrite@$DATABASE_NAME" not in update_command
