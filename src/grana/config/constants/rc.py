"""Runtime configuration module"""

from __future__ import annotations

import dataclasses
import logging
import pathlib
import typing as t

import yaml

from .cache import CACHE
from ...loader.utils import ExpressionYAMLLoader
from ...tools.classloader import from_dict
from ...tools.proxy import DeferredCallsProxy

logger = DeferredCallsProxy(logging.getLogger(__name__))

__all__ = [
    "RC",
    "logger",
    "sentinel",
]


class ConfigSentinel:
    """Sentinel type for runtime configuration parameters"""


sentinel = ConfigSentinel()


@dataclasses.dataclass
class RC:
    """Runtime configuration"""

    log_level: t.Union[str, ConfigSentinel] = sentinel
    log_file: t.Union[str, ConfigSentinel] = sentinel
    workflow_file: t.Union[pathlib.Path, ConfigSentinel] = sentinel
    workflow_loader_source_file: t.Union[pathlib.Path, ConfigSentinel] = sentinel
    display_source_file: t.Union[pathlib.Path, ConfigSentinel] = sentinel
    display_name: t.Union[str, ConfigSentinel] = sentinel
    strategy: t.Union[str, ConfigSentinel] = sentinel
    force_color: t.Union[bool, ConfigSentinel] = sentinel
    default_shell_executable: t.Union[str, ConfigSentinel] = sentinel
    shell_inject_yield_function: t.Union[bool, ConfigSentinel] = sentinel
    strict_outcomes_rendering: t.Union[bool, ConfigSentinel] = sentinel
    action_classes_directories: t.Union[list[pathlib.Path], ConfigSentinel] = sentinel
    external_python_modules_paths: t.Union[list[pathlib.Path], ConfigSentinel] = sentinel
    strict: t.Union[bool, ConfigSentinel] = sentinel
    subprocess_stream_buffer_limit: t.Union[int, ConfigSentinel] = sentinel

    @classmethod
    @CACHE.wrap
    def build(cls) -> RC:
        """Load from file"""
        from . import C
        from ...rendering import CommonTemplar

        rc_file_path: pathlib.Path = C.RC_FILE
        if not rc_file_path.is_file():
            logger.debug(f"No RC file found at {str(rc_file_path)!r}")
            return RC()
        logger.info(f"Loading RC file: {str(rc_file_path)!r}")
        with rc_file_path.open() as f:
            config_data: dict = t.cast(dict, yaml.load(f, ExpressionYAMLLoader))  # nosec
        templar: CommonTemplar = CommonTemplar.from_source_file(rc_file_path)
        rendered_data: t.Dict[str, t.Any] = templar.render(config_data)
        return from_dict(data_type=RC, data=rendered_data)
