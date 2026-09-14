"""
Tests for instance creation helpers.
"""

from pathlib import Path
from unittest import mock

import pytest

from launchpad.cli import instance_create
from launchpad.exceptions import ConfigurationError, KubernetesError
from launchpad.utils import (
    config_belongs_to_instance,
    load_yaml,
    overlay_identity_config,
    patch_application_identity,
    slugify,
    write_yaml,
)

FAKE_TEMPLATE = "/fake/instance-template"


def _dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_yaml(path, data)


def _load(path: Path) -> dict:
    return load_yaml(path)


def _source_config(slug: str = "foo") -> dict:
    return {
        "K8S_NAMESPACE": slug,
        "TUTOR_APP_NAME": slug,
        "LMS_HOST": f"{slug}.cluster.domain",
        "CMS_HOST": f"studio.{slug}.cluster.domain",
        "MYSQL_DATABASE": f"launchpad-{slug}-openedx",
        "MYSQL_USERNAME": f"launchpad-{slug}",
        "MYSQL_PASSWORD": "old-mysql-pass",
        "S3_STORAGE_BUCKET": f"launchpad-{slug}-oldbuck",
        "TUTOR_VERSION": "v20.0.5",
        "PLATFORM_NAME": "Copied Platform",
        "PICASSO_EXTRA_COMMANDS": ["custom-plugin"],
        "OPENEDX_EXTRA_PIP_REQUIREMENTS": ["some-pkg"],
    }


def _source_application(slug: str = "foo") -> dict:
    return {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Application",
        "metadata": {
            "name": f"{slug}-production",
            "namespace": "argocd",
            "labels": {
                "app.kubernetes.io/name": slug,
                "app.kubernetes.io/instance": "production",
            },
            "annotations": {"custom": "keep-me"},
        },
        "spec": {
            "source": {
                "path": f"instances/{slug}/env",
                "repoURL": "https://github.com/old/repo.git",
                "targetRevision": "old-branch",
            },
            "destination": {
                "server": "https://kubernetes.default.svc",
                "namespace": slug,
            },
            "syncPolicy": {"automated": {"enabled": False, "prune": True}},
        },
    }


def _generated_config(slug: str) -> dict:
    return {
        "K8S_NAMESPACE": slug,
        "TUTOR_APP_NAME": slug,
        "LMS_HOST": f"{slug}.cluster.domain",
        "CMS_HOST": f"studio.{slug}.cluster.domain",
        "PREVIEW_LMS_HOST": f"preview.{slug}.cluster.domain",
        "MYSQL_DATABASE": f"launchpad-{slug}-openedx",
        "MYSQL_USERNAME": f"launchpad-{slug}",
        "MYSQL_PASSWORD": "generated-mysql-pass",
        "MYSQL_HOST": "mysql.cluster.domain",
        "MYSQL_PORT": "3306",
        "MONGODB_DATABASE": f"launchpad-{slug}-openedx",
        "MONGODB_USERNAME": f"launchpad-{slug}",
        "MONGODB_PASSWORD": "generated-mongo-pass",
        "MONGODB_HOST": "mongodb.cluster.domain",
        "MONGODB_PORT": "27017",
        "MONGODB_AUTH_SOURCE": "admin",
        "MONGODB_REPLICA_SET": "",
        "FORUM_MONGODB_DATABASE": f"launchpad-{slug}-forum",
        "MFE_DOCKER_IMAGE": f"ghcr.io/org/repo:{slug}-mfe",
        "DOCKER_IMAGE_OPENEDX": f"ghcr.io/org/repo:{slug}-openedx",
        "DOCKER_IMAGE_OPENEDX_DEV": f"ghcr.io/org/repo:{slug}-openedx-dev",
        "DOCKER_REGISTRY": "ghcr.io",
        "DRYDOCK_REGISTRY_CREDENTIALS": "generated-creds",
        "OPENEDX_AWS_ACCESS_KEY": "generated-key",
        "OPENEDX_AWS_SECRET_ACCESS_KEY": "generated-secret",
        "S3_STORAGE_BUCKET": f"launchpad-{slug}-newbuck",
        "S3_REGION": "nyc3",
        "S3_HOST": "nyc3.digitaloceanspaces.com",
        "S3_USE_SSL": True,
        "TUTOR_VERSION": "v-generated",
        "PLATFORM_NAME": "Generated Platform",
        "PICASSO_EXTRA_COMMANDS": ["from-template"],
    }


def _generated_application(slug: str) -> dict:
    return {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Application",
        "metadata": {
            "name": f"{slug}-production",
            "namespace": "argocd",
            "labels": {
                "app.kubernetes.io/name": slug,
                "app.kubernetes.io/instance": "production",
                "app.kubernetes.io/managed-by": "argocd",
            },
        },
        "spec": {
            "source": {
                "path": f"instances/{slug}/env",
                "repoURL": "https://github.com/org/repo.git",
                "targetRevision": "main",
            },
            "destination": {
                "server": "https://kubernetes.default.svc",
                "namespace": slug,
            },
            "syncPolicy": {"automated": {"enabled": True, "prune": True}},
        },
    }


def fake_cookiecutter(_template, **kwargs):
    output_dir = Path(kwargs["output_dir"])
    slug = slugify(kwargs["extra_context"]["instance_name"])
    dest = output_dir / slug
    dest.mkdir(parents=True, exist_ok=True)
    _dump(dest / "config.yml", _generated_config(slug))
    _dump(dest / "application.yml", _generated_application(slug))


def generate(instances_dir: Path, name: str, **kwargs) -> None:
    instance_create._generate_instance_config(
        name,
        FAKE_TEMPLATE,
        None,
        None,
        None,
        None,
        None,
        instances_dir,
        "cluster.domain",
        "production",
        **kwargs,
    )


@pytest.fixture
def mock_git():
    with mock.patch.multiple(
        "launchpad.cli.instance_create",
        get_git_repo_url=mock.DEFAULT,
        get_git_repo_branch=mock.DEFAULT,
        parse_repo_owner=mock.DEFAULT,
        parse_repo_name=mock.DEFAULT,
    ) as mocks:
        mocks["get_git_repo_url"].return_value = "https://github.com/org/repo.git"
        mocks["get_git_repo_branch"].return_value = "main"
        mocks["parse_repo_owner"].return_value = "org"
        mocks["parse_repo_name"].return_value = "repo"
        yield mocks


class TestConfigBelongsToInstance:
    """Tests for config_belongs_to_instance."""

    def test_matches_k8s_namespace(self):
        assert config_belongs_to_instance({"K8S_NAMESPACE": "bar"}, "bar")

    def test_matches_tutor_app_name(self):
        assert config_belongs_to_instance({"TUTOR_APP_NAME": "bar"}, "bar")

    def test_rejects_other_instance(self):
        assert not config_belongs_to_instance(
            {"K8S_NAMESPACE": "foo", "TUTOR_APP_NAME": "foo"}, "bar"
        )


class TestOverlayIdentityConfig:
    """Tests for overlay_identity_config."""

    def test_overwrites_identity_keys_and_keeps_extras(self):
        source = _source_config("foo")
        generated = _generated_config("bar")

        result = overlay_identity_config(source, generated)

        assert result["K8S_NAMESPACE"] == "bar"
        assert result["MYSQL_PASSWORD"] == "generated-mysql-pass"
        assert result["S3_STORAGE_BUCKET"] == "launchpad-bar-newbuck"
        assert result["TUTOR_VERSION"] == "v20.0.5"
        assert result["PLATFORM_NAME"] == "Copied Platform"
        assert result["PICASSO_EXTRA_COMMANDS"] == ["custom-plugin"]
        assert result["OPENEDX_EXTRA_PIP_REQUIREMENTS"] == ["some-pkg"]


class TestPatchApplicationIdentity:
    """Tests for patch_application_identity."""

    def test_patches_identity_and_keeps_sync_policy(self):
        application = _source_application("foo")
        generated = _generated_application("bar")

        result = patch_application_identity(application, generated)

        assert result["metadata"]["name"] == "bar-production"
        assert result["metadata"]["labels"]["app.kubernetes.io/name"] == "bar"
        assert result["metadata"]["annotations"]["custom"] == "keep-me"
        assert result["spec"]["source"]["path"] == "instances/bar/env"
        assert result["spec"]["source"]["repoURL"] == "https://github.com/org/repo.git"
        assert result["spec"]["source"]["targetRevision"] == "main"
        assert result["spec"]["destination"]["namespace"] == "bar"
        assert result["spec"]["syncPolicy"]["automated"]["enabled"] is False


class TestGenerateInstanceConfig:
    """Tests for _generate_instance_config modes."""

    @mock.patch(
        "launchpad.cli.instance_create.cookiecutter", side_effect=fake_cookiecutter
    )
    def test_fresh_create_calls_cookiecutter_on_dest(
        self, mock_cookiecutter, mock_git, tmp_path
    ):
        generate(tmp_path, "bar")

        mock_cookiecutter.assert_called_once()
        assert mock_cookiecutter.call_args.kwargs["output_dir"] == str(tmp_path)
        assert (tmp_path / "bar" / "config.yml").exists()
        assert (tmp_path / "bar" / "application.yml").exists()
        assert mock_git["get_git_repo_url"].called

    @mock.patch("launchpad.cli.instance_create.cookiecutter")
    def test_matching_config_skips_cookiecutter(self, mock_cookiecutter, tmp_path):
        dest = tmp_path / "bar"
        original = _source_config("bar")
        original["MYSQL_PASSWORD"] = "keep-this-password"
        _dump(dest / "config.yml", original)
        _dump(dest / "application.yml", _source_application("bar"))

        generate(tmp_path, "bar")

        mock_cookiecutter.assert_not_called()
        assert _load(dest / "config.yml")["MYSQL_PASSWORD"] == "keep-this-password"

    @mock.patch(
        "launchpad.cli.instance_create.cookiecutter", side_effect=fake_cookiecutter
    )
    def test_matching_config_generates_missing_application(
        self, mock_cookiecutter, mock_git, tmp_path
    ):
        dest = tmp_path / "bar"
        original = _source_config("bar")
        original["MYSQL_PASSWORD"] = "keep-this-password"
        _dump(dest / "config.yml", original)

        generate(tmp_path, "bar")

        mock_cookiecutter.assert_called_once()
        assert mock_cookiecutter.call_args.kwargs["output_dir"] != str(tmp_path)
        assert _load(dest / "config.yml")["MYSQL_PASSWORD"] == "keep-this-password"
        application = _load(dest / "application.yml")
        assert application["metadata"]["name"] == "bar-production"
        assert application["spec"]["syncPolicy"]["automated"]["enabled"] is True
        assert mock_git["get_git_repo_url"].called

    @mock.patch(
        "launchpad.cli.instance_create.cookiecutter", side_effect=fake_cookiecutter
    )
    def test_mismatched_slug_rebases_without_replacing_extras(
        self, mock_cookiecutter, mock_git, tmp_path
    ):
        dest = tmp_path / "bar"
        _dump(dest / "config.yml", _source_config("foo"))
        _dump(dest / "application.yml", _source_application("foo"))

        generate(tmp_path, "bar")

        mock_cookiecutter.assert_called_once()
        assert mock_cookiecutter.call_args.kwargs["output_dir"] != str(tmp_path)

        config = _load(dest / "config.yml")
        assert config["K8S_NAMESPACE"] == "bar"
        assert config["MYSQL_PASSWORD"] == "generated-mysql-pass"
        assert config["S3_STORAGE_BUCKET"] == "launchpad-bar-newbuck"
        assert config["TUTOR_VERSION"] == "v20.0.5"
        assert config["PICASSO_EXTRA_COMMANDS"] == ["custom-plugin"]
        assert config["MYSQL_PASSWORD"] != "old-mysql-pass"

        application = _load(dest / "application.yml")
        assert application["metadata"]["name"] == "bar-production"
        assert application["metadata"]["annotations"]["custom"] == "keep-me"
        assert application["spec"]["syncPolicy"]["automated"]["enabled"] is False
        assert application["spec"]["destination"]["namespace"] == "bar"
        assert mock_git["get_git_repo_url"].called

    @mock.patch(
        "launchpad.cli.instance_create.cookiecutter", side_effect=fake_cookiecutter
    )
    def test_from_instance_copies_and_rebases(
        self, mock_cookiecutter, mock_git, tmp_path
    ):
        source = tmp_path / "foo"
        _dump(source / "config.yml", _source_config("foo"))
        _dump(source / "application.yml", _source_application("foo"))

        generate(tmp_path, "bar", from_instance="foo")

        mock_cookiecutter.assert_called_once()
        config = _load(tmp_path / "bar" / "config.yml")
        assert config["K8S_NAMESPACE"] == "bar"
        assert config["PICASSO_EXTRA_COMMANDS"] == ["custom-plugin"]
        assert config["MYSQL_PASSWORD"] == "generated-mysql-pass"

        application = _load(tmp_path / "bar" / "application.yml")
        assert application["metadata"]["labels"]["app.kubernetes.io/name"] == "bar"
        assert application["spec"]["syncPolicy"]["automated"]["enabled"] is False
        assert mock_git["parse_repo_name"].called

    @mock.patch("launchpad.cli.instance_create.cookiecutter")
    def test_from_instance_errors_when_dest_already_matches(
        self, mock_cookiecutter, tmp_path
    ):
        _dump((tmp_path / "foo" / "config.yml"), _source_config("foo"))
        _dump((tmp_path / "bar" / "config.yml"), _source_config("bar"))

        with pytest.raises(ConfigurationError, match="already has matching"):
            generate(tmp_path, "bar", from_instance="foo")

        mock_cookiecutter.assert_not_called()

    @mock.patch("launchpad.cli.instance_create.cookiecutter")
    def test_from_instance_same_name_errors(self, mock_cookiecutter, tmp_path):
        with pytest.raises(ConfigurationError, match="same instance name"):
            generate(tmp_path, "bar", from_instance="bar")

        mock_cookiecutter.assert_not_called()

    @mock.patch("launchpad.cli.instance_create.cookiecutter")
    def test_directory_without_config_raises(self, mock_cookiecutter, tmp_path):
        (tmp_path / "bar").mkdir()

        with pytest.raises(FileNotFoundError, match="config.yml is missing"):
            generate(tmp_path, "bar")

        mock_cookiecutter.assert_not_called()

    @mock.patch(
        "launchpad.cli.instance_create.cookiecutter", side_effect=fake_cookiecutter
    )
    def test_missing_application_falls_back_to_generated(
        self, _mock_cookiecutter, mock_git, tmp_path
    ):
        dest = tmp_path / "bar"
        _dump(dest / "config.yml", _source_config("foo"))

        generate(tmp_path, "bar")

        application = _load(dest / "application.yml")
        assert application["metadata"]["name"] == "bar-production"
        assert application["spec"]["syncPolicy"]["automated"]["enabled"] is True
        assert mock_git["parse_repo_owner"].called


class TestCreateProvisionWorkflows:
    """Tests for _create_provision_workflows."""

    @mock.patch("launchpad.cli.instance_create.log_success")
    @mock.patch("launchpad.cli.instance_create.subprocess.run")
    @mock.patch("launchpad.cli.instance_create.wait_for_workflow_completion")
    @mock.patch("launchpad.cli.instance_create.run_command_with_logging")
    def test_deletes_existing_workflows_before_apply(
        self, mock_rcl, mock_wait, mock_subprocess_run, mock_log_success
    ):
        mock_wait.return_value = True

        instance_create._create_provision_workflows(
            mock.Mock(),
            "test-instance",
            "https://example.com/manifests",
            {},
        )

        delete_calls = [
            c
            for c in mock_subprocess_run.call_args_list
            if c[0][0][:3] == ["kubectl", "delete", "workflow"]
        ]
        assert len(delete_calls) == 6
        assert mock_subprocess_run.call_args_list[0][0][0][:3] == [
            "kubectl",
            "delete",
            "workflow",
        ]
        assert "--ignore-not-found=true" in mock_subprocess_run.call_args_list[0][0][0]
        assert mock_rcl.call_count == 3
        mock_log_success.assert_called_once()

    @mock.patch("launchpad.cli.instance_create.subprocess.run")
    @mock.patch("launchpad.cli.instance_create.wait_for_workflow_completion")
    @mock.patch("launchpad.cli.instance_create.run_command_with_logging")
    def test_raises_when_any_workflow_fails(self, _mock_rcl, mock_wait, _mock_run):
        mock_wait.side_effect = [True, False, True]

        with pytest.raises(KubernetesError, match="test-instance"):
            instance_create._create_provision_workflows(
                mock.Mock(),
                "test-instance",
                "https://example.com/manifests",
                {},
            )
