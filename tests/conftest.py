"""Session-wide fixtures"""

import sys
from pathlib import Path

import pytest

from grana import logging
from grana.config.constants import C


def pytest_sessionstart():
    """Add sources to sys.path"""
    source_dir: Path = Path(__file__).parents[1] / "src"
    assert source_dir.is_dir()
    sys.path.append(str(source_dir))


@pytest.fixture(autouse=True, scope="session")
def configure_logging() -> None:
    """Establish logging configuration"""
    logging.configure_logging(level="DEBUG", colorize=True)


@pytest.fixture(autouse=True, scope="function")
def reset_constants_cache() -> None:
    """Reset constants cache before each test"""
    C.cache_clear()
