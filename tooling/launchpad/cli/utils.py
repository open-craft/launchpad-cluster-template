"""
Utility functions for CLI.
"""

import logging
import sys
from typing import Callable, TypeVar

T = TypeVar("T")


def run_command_with_logging(
    logger: logging.Logger, description: str, func: Callable[..., T], *args, **kwargs
) -> T:
    """
    Run a command with logging for CLI operations.

    This is specifically for CLI commands to provide user-friendly output.
    Internal library code should do its own logging.

    Args:
        logger: Logger instance
        description: Description of the command (will be capitalized and logged)
        func: Function to run
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of the function

    Raises:
        Exception: If the command fails
    """

    logger.info(description)

    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error("Failed to %s: %s", description, e)
        raise


def exit_with_error(
    logger: logging.Logger, message: str, exc_info: bool = True
) -> None:
    """
    Exit with error.

    Args:
        message: Error message
        exc_info: Whether to include exception information

    Returns:
        None
    """

    logger.error(message, exc_info=exc_info)
    sys.exit(1)
