"""
Semantic layer logger — thin wrapper around Python logging.

Usage:
    from semantic.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Processing %d files", count)
"""
import logging
import sys

def get_logger(name: str) -> logging.Logger:
    """Get a named logger for a semantic module."""
    return logging.getLogger(name)

def configure_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure root logging level based on CLI flags.

    verbose=True  → DEBUG level (all details)
    quiet=True    → ERROR level (errors only, to stderr)
    default       → INFO level
    """
    root = logging.getLogger()

    # Set level
    if quiet:
        root.setLevel(logging.ERROR)
    elif verbose:
        root.setLevel(logging.DEBUG)
    else:
        root.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    root.handlers.clear()

    # Add stderr handler with simple format
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    root.addHandler(handler)
