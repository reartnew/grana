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

    log_level: t.Union[str, ConfigSentinel] = sentinel
    log_file: t.Union[str, ConfigSentinel] = sentinel
    workflow_source_file: t.Union[pathlib.Path, ConfigSentinel] = sentinel
    workflow_loader_source_file: t.Union[pathlib.Path, ConfigSentinel] = sentinel
    display_source_file: t.Union[pathlib.Path, ConfigSentinel] = sentinel
    display_name: t.Union[str, ConfigSentinel] = sentinel
    strategy_name: t.Union[str, ConfigSentinel] = sentinel
    use_color: t.Union[bool, ConfigSentinel] = sentinel
    default_shell_executable: t.Union[str, ConfigSentinel] = sentinel
    shell_inject_yield_function: t.Union[bool, ConfigSentinel] = sentinel
    strict_outcomes_rendering: t.Union[bool, ConfigSentinel] = sentinel
    action_classes_directories: t.Union[list[pathlib.Path], ConfigSentinel] = sentinel
    external_python_modules_paths: t.Union[list[pathlib.Path], ConfigSentinel] = sentinel

    def __post_init__(self) -> None:
        if self.display_source_file is not sentinel and self.display_name is not sentinel:
            raise ValueError("Mutually exclusive options `display_source_file` and `display_name` have been provided")

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
