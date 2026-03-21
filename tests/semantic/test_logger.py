"""
Tests for semantic.logger module
"""
import logging

from semantic.logger import configure_logging, get_logger


def test_get_logger_returns_logger():
    """Verify get_logger returns a Logger instance"""
    logger = get_logger(__name__)
    assert isinstance(logger, logging.Logger)
    assert logger.name == __name__


def test_configure_logging_verbose():
    """Verify root level is DEBUG after verbose=True"""
    configure_logging(verbose=True, quiet=False)
    root = logging.getLogger()
    assert root.level == logging.DEBUG


def test_configure_logging_quiet():
    """Verify root level is ERROR after quiet=True"""
    configure_logging(verbose=False, quiet=True)
    root = logging.getLogger()
    assert root.level == logging.ERROR


def test_configure_logging_default():
    """Verify root level is INFO by default"""
    configure_logging(verbose=False, quiet=False)
    root = logging.getLogger()
    assert root.level == logging.INFO
