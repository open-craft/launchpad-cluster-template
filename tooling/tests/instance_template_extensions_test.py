"""
Tests for instance-template Jinja helpers.
"""

import importlib.util
from pathlib import Path

import pytest

EXTENSIONS_PATH = (
    Path(__file__).resolve().parents[2] / "instance-template" / "extensions.py"
)


def _load_extensions():
    """Load instance-template/extensions.py without installing it."""

    spec = importlib.util.spec_from_file_location(
        "instance_template_extensions", EXTENSIONS_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="extensions")
def fixture_extensions():
    """Provide the instance-template extensions module."""

    return _load_extensions()


class TestEnv:
    """
    Tests for blank environment values.
    """

    def test_blank_value_uses_default(self, monkeypatch, extensions):
        """
        Test that an empty environment variable uses the default.
        """

        monkeypatch.setenv("LAUNCHPAD_MYSQL_PORT", "   ")

        assert extensions.env("LAUNCHPAD_MYSQL_PORT", "3306") == "3306"

    def test_unset_value_uses_default(self, monkeypatch, extensions):
        """
        Test that a missing environment variable uses the default.
        """

        monkeypatch.delenv("LAUNCHPAD_MYSQL_PORT", raising=False)

        assert extensions.env("LAUNCHPAD_MYSQL_PORT", "3306") == "3306"

    def test_set_value_is_kept(self, monkeypatch, extensions):
        """
        Test that a non-blank environment variable is returned unchanged.
        """

        monkeypatch.setenv("LAUNCHPAD_MYSQL_PORT", "3307")

        assert extensions.env("LAUNCHPAD_MYSQL_PORT", "3306") == "3307"


class TestMongoDBPort:
    """
    Tests for the MongoDB port written into Tutor settings.
    """

    def test_explicit_port_is_kept(self, extensions):
        """
        Test that an explicit port is used for any host.
        """

        assert (
            extensions.mongodb_port("mongodb+srv://cluster.example.net", "27018")
            == "27018"
        )

    def test_srv_host_without_port_renders_none(self, extensions):
        """
        Test that an Atlas SRV host renders the Python expression None.
        """

        assert (
            extensions.mongodb_port("mongodb+srv://cluster.example.net", "") == "None"
        )

    def test_plain_host_without_port_defaults_to_27017(self, extensions):
        """
        Test that a non-SRV host defaults to port 27017.
        """

        assert extensions.mongodb_port("mongodb.cluster.domain", "   ") == "27017"
