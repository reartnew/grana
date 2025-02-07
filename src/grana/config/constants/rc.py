"""Runtime configuration module"""

from __future__ import annotations

import dataclasses
import logging
import pathlib
import typing as t

import yaml

from ...tools.classloader import from_dict
from ...tools.proxy import DeferredCallsProxy

logger = DeferredCallsProxy(logging.getLogger(__name__))

__all__ = [
    "RC",
    "logger",
    "sentinel",
]


class ConfigSentinel:
    """Sentinel type for configuration parameters"""


sentinel = ConfigSentinel()


@dataclasses.dataclass(kw_only=True)
class RC:
    """Runtime configuration"""

    log_level: str | ConfigSentinel = sentinel
    log_file: str | ConfigSentinel = sentinel

    @classmethod
    def build(cls) -> RC:
        """Load from file"""
        # pylint: disable=import-outside-toplevel
        from . import C

        rc_file_path: pathlib.Path = C.RC_FILE
        if not rc_file_path.is_file():
            logger.debug(f"No RC file found at {str(rc_file_path)!r}")
            return RC()
        logger.info(f"Loading RC file: {str(rc_file_path)!r}")
        with rc_file_path.open() as f:
            config_data: dict = t.cast(dict, yaml.safe_load(f))
        return from_dict(RC, config_data)
