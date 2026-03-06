"""
Unit tests for the utility functions.
"""

import logging
import os
import tempfile
from unittest import mock

import pytest

from launchpad.exceptions import CommandNotFoundError, ConfigurationError
from launchpad.utils import (
    ColoredFormatter,
    build_instance_config,
    check_command_installed,
    check_env_var_set,
    get_logger,
    log_success,
    sanitize_username,
)


class TestColoredFormatter:
    """
    Test suite for ColoredFormatter.
    """

    def test_colored_formatter_initialization(self):
        """
        Test ColoredFormatter initialization.
        """

        formatter = ColoredFormatter()

        assert formatter is not None
        assert hasattr(formatter, "COLORS")

    def test_colored_formatter_colors_defined(self):
        """
        Test that all log levels have colors defined.
        """

        formatter = ColoredFormatter()

        assert "DEBUG" in formatter.COLORS
        assert "INFO" in formatter.COLORS
        assert "WARNING" in formatter.COLORS
        assert "ERROR" in formatter.COLORS
        assert "CRITICAL" in formatter.COLORS
        assert "SUCCESS" in formatter.COLORS
        assert "RESET" in formatter.COLORS

    def test_colored_formatter_format_info(self):
        """
        Test formatting of INFO level log record.
        """

        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        assert "INFO" in formatted
        assert "Test message" in formatted
        assert "\033[" in formatted

    def test_colored_formatter_format_error(self):
        """
        Test formatting of ERROR level log record.
        """

        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        assert "ERROR" in formatted
        assert "Error message" in formatted
        assert "\033[" in formatted

    def test_colored_formatter_format_success(self):
        """
        Test formatting of SUCCESS level log record.
        """

        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Success message",
            args=(),
            exc_info=None,
        )
        record.levelname = "SUCCESS"

        formatted = formatter.format(record)

        assert "SUCCESS" in formatted
        assert "Success message" in formatted


class TestGetLogger:
    """
    Test suite for get_logger function.
    """

    @mock.patch("launchpad.utils.get_config")
    def test_get_logger_returns_logger(self, mock_get_config):
        """
        Test that get_logger returns a logging.Logger instance.
        """

        mock_config = mock.Mock()
        mock_config.log_level = "INFO"
        mock_config.log_file = "test.log"
        mock_get_config.return_value = mock_config

        logger = get_logger("test_logger")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

        logger.handlers.clear()

    @mock.patch("launchpad.utils.get_config")
    def test_get_logger_sets_log_level(self, mock_get_config):
        """
        Test that get_logger sets the correct log level.
        """

        mock_config = mock.Mock()
        mock_config.log_level = "DEBUG"
        mock_config.log_file = "test.log"
        mock_get_config.return_value = mock_config

        logger = get_logger("test_logger_debug")

        assert logger.level == logging.DEBUG

        logger.handlers.clear()

    @mock.patch("launchpad.utils.get_config")
    def test_get_logger_adds_handlers(self, mock_get_config):
        """
        Test that get_logger adds console and file handlers.
        """

        mock_config = mock.Mock()
        mock_config.log_level = "INFO"
        mock_config.log_file = "test.log"
        mock_get_config.return_value = mock_config

        logger = get_logger("test_logger_handlers")

        assert len(logger.handlers) == 2

        logger.handlers.clear()

    @mock.patch("launchpad.utils.get_config")
    def test_get_logger_reuses_existing_logger(self, mock_get_config):
        """
        Test that get_logger reuses an existing logger with handlers.
        """

        mock_config = mock.Mock()
        mock_config.log_level = "INFO"
        mock_config.log_file = "test.log"
        mock_get_config.return_value = mock_config

        logger1 = get_logger("test_logger_reuse")
        logger2 = get_logger("test_logger_reuse")

        assert logger1 is logger2

        assert len(logger1.handlers) == 2

        logger1.handlers.clear()

    @mock.patch("launchpad.utils.get_config")
    def test_get_logger_uses_colored_formatter(self, mock_get_config):
        """
        Test that get_logger uses ColoredFormatter for console output.
        """

        mock_config = mock.Mock()
        mock_config.log_level = "INFO"
        mock_config.log_file = "test.log"
        mock_get_config.return_value = mock_config

        logger = get_logger("test_logger_formatter")

        console_handler = logger.handlers[0]
        assert isinstance(console_handler, logging.StreamHandler)
        assert isinstance(console_handler.formatter, ColoredFormatter)

        logger.handlers.clear()


class TestLogSuccess:
    """
    Test suite for log_success function.
    """

    @mock.patch("launchpad.utils.get_config")
    def test_log_success_creates_success_record(self, mock_get_config):
        """
        Test that log_success creates a log record with SUCCESS level.
        """

        mock_config = mock.Mock()
        mock_config.log_level = "INFO"
        mock_config.log_file = "test.log"
        mock_get_config.return_value = mock_config

        logger = get_logger("test_log_success")

        with mock.patch.object(logger, "handle") as mock_handle:
            log_success(logger, "Success message")

            mock_handle.assert_called_once()
            record = mock_handle.call_args[0][0]
            assert record.levelname == "SUCCESS"
            assert record.getMessage() == "Success message"

        logger.handlers.clear()

    @mock.patch("launchpad.utils.get_config")
    def test_log_success_uses_info_level(self, mock_get_config):
        """
        Test that log_success uses INFO level internally.
        """

        mock_config = mock.Mock()
        mock_config.log_level = "INFO"
        mock_config.log_file = "test.log"
        mock_get_config.return_value = mock_config

        logger = get_logger("test_log_success_level")

        with mock.patch.object(logger, "handle") as mock_handle:
            log_success(logger, "Test success")

            record = mock_handle.call_args[0][0]
            assert record.levelno == logging.INFO

        logger.handlers.clear()


class TestCheckEnvVarSet:
    """
    Test suite for check_env_var_set function.
    """

    def test_check_env_var_set_exists(self):
        """
        Test that check_env_var_set passes when variable is set.
        """

        with mock.patch.dict(os.environ, {"TEST_VAR": "value"}):

            check_env_var_set("TEST_VAR")

    def test_check_env_var_set_missing(self):
        """
        Test that check_env_var_set raises ConfigurationError when variable is missing.
        """

        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ConfigurationError, match="Environment variable TEST_MISSING is not set"
            ):
                check_env_var_set("TEST_MISSING")

    def test_check_env_var_set_empty(self):
        """
        Test that check_env_var_set raises ConfigurationError when variable is empty.
        """

        with mock.patch.dict(os.environ, {"TEST_EMPTY": ""}):
            with pytest.raises(
                ConfigurationError, match="Environment variable TEST_EMPTY is not set"
            ):
                check_env_var_set("TEST_EMPTY")


class TestCheckCommandInstalled:
    """
    Test suite for check_command_installed function.
    """

    def test_check_command_installed_exists(self):
        """
        Test that check_command_installed passes for existing command.
        """

        check_command_installed("python")

    def test_check_command_installed_missing(self):
        """
        Test that check_command_installed raises CommandNotFoundError for missing command.
        """

        with pytest.raises(
            CommandNotFoundError,
            match="nonexistent_command_xyz command is not installed",
        ):
            check_command_installed("nonexistent_command_xyz")

    @mock.patch("launchpad.utils.shutil.which")
    def test_check_command_installed_mock(self, mock_which):
        """
        Test check_command_installed with mocked shutil.which.
        """

        mock_which.return_value = "/usr/bin/test_command"

        check_command_installed("test_command")

        mock_which.assert_called_once_with("test_command")

    @mock.patch("launchpad.utils.shutil.which")
    def test_check_command_installed_mock_missing(self, mock_which):
        """
        Test check_command_installed raises error when command not found.
        """

        mock_which.return_value = None

        with pytest.raises(
            CommandNotFoundError, match="missing_cmd command is not installed"
        ):
            check_command_installed("missing_cmd")


class TestUtilsIntegration:
    """
    Integration tests for utility functions.
    """

    def test_logger_writes_to_file(self):
        """
        Test that logger writes to file correctly.
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")

            with mock.patch("launchpad.utils.get_config") as mock_get_config:
                mock_config = mock.Mock()
                mock_config.log_level = "INFO"
                mock_config.log_file = log_file
                mock_get_config.return_value = mock_config

                logger = get_logger("test_file_logger")
                logger.info("Test message")

                assert os.path.exists(log_file)
                with open(log_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    assert "Test message" in content

                logger.handlers.clear()

    @mock.patch.dict(os.environ, {"TEST_VAR": "test_value"})
    def test_check_env_and_command_integration(self):
        """
        Test integration of environment and command checks.
        """

        check_env_var_set("TEST_VAR")
        check_command_installed("python")

        with pytest.raises(ConfigurationError):
            check_env_var_set("NONEXISTENT_VAR")

        with pytest.raises(CommandNotFoundError):
            check_command_installed("nonexistent_cmd")


class TestSanitizeUsername:
    """
    Tests for sanitize_username.
    """

    def test_basic_email(self):
        assert sanitize_username("User@Example.com") == "user-example.com"

    def test_invalid_chars_collapsed(self):
        assert sanitize_username("a@@@b___c..d--e") == "a-b-c.d-e"

    def test_trim_edges(self):
        assert sanitize_username("--.name.--") == "name"

    def test_only_invalid_raises(self):
        with pytest.raises(ValueError):
            sanitize_username("@@@@")


class TestBuildInstanceConfigMongoDB:
    """
    Tests for MongoDB parameter extraction in build_instance_config.
    """

    def test_mongodb_connection_params_extracted(self):
        """
        Test that all MongoDB connection parameters are extracted correctly.
        """
        config = {
            "MONGODB_DATABASE": "testdb",
            "FORUM_MONGODB_DATABASE": "testdb_forum",
            "MONGODB_USERNAME": "user",
            "MONGODB_PASSWORD": "pass",
            "MONGODB_HOST": "mongo.cluster.domain",
            "MONGODB_PORT": "27017",
            "MONGODB_USE_SSL": True,
            "MONGODB_AUTH_MECHANISM": "SCRAM-SHA-1",
            "MONGODB_AUTH_SOURCE": "admin",
            "MONGODB_REPLICA_SET": "rs0",
        }

        result = build_instance_config("inst", config)

        assert result["LAUNCHPAD_INSTANCE_MONGODB_DATABASE"] == "testdb"
        assert result["LAUNCHPAD_INSTANCE_MONGODB_DATABASE_FORUM"] == "testdb_forum"
        assert result["LAUNCHPAD_INSTANCE_MONGODB_USERNAME"] == "user"
        assert result["LAUNCHPAD_INSTANCE_MONGODB_PASSWORD"] == "pass"
        assert result["LAUNCHPAD_INSTANCE_MONGODB_HOST"] == "mongo.cluster.domain"
        assert result["LAUNCHPAD_INSTANCE_MONGODB_PORT"] == "27017"
        assert result["LAUNCHPAD_INSTANCE_MONGODB_AUTH_SOURCE"] == "admin"
        assert result["LAUNCHPAD_INSTANCE_MONGODB_REPLICA_SET"] == "rs0"

    def test_mongodb_empty_values_handled(self):
        """
        Test that empty or missing MongoDB values return empty strings.
        """
        config = {
            "MONGODB_DATABASE": "testdb",
            "MONGODB_USERNAME": "user",
            "MONGODB_PASSWORD": "pass",
        }

        result = build_instance_config("inst", config)

        assert result["LAUNCHPAD_INSTANCE_MONGODB_DATABASE"] == "testdb"
        assert result["LAUNCHPAD_INSTANCE_MONGODB_HOST"] == ""
        assert result["LAUNCHPAD_INSTANCE_MONGODB_PORT"] == ""
        assert result["LAUNCHPAD_INSTANCE_MONGODB_AUTH_SOURCE"] == ""
        assert result["LAUNCHPAD_INSTANCE_MONGODB_REPLICA_SET"] == ""
        assert result["LAUNCHPAD_INSTANCE_MONGODB_DATABASE_FORUM"] == ""
