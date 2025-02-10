"""Runtime configuration module"""

from __future__ import annotations

import dataclasses
import functools
import logging
import os
import pathlib
import typing as t

import yaml

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

    @classmethod
    @functools.lru_cache(maxsize=1)
    def build(cls) -> RC:
        """Load from file"""
        # pylint: disable=import-outside-toplevel,cyclic-import
        from . import C
        from ...rendering import CommonTemplar, containers as c

        rc_file_path: pathlib.Path = C.RC_FILE
        if not rc_file_path.is_file():
            logger.debug(f"No RC file found at {str(rc_file_path)!r}")
            return RC()
        logger.info(f"Loading RC file: {str(rc_file_path)!r}")
        with rc_file_path.open() as f:
            config_data: dict = t.cast(dict, yaml.load(f, ExpressionYAMLLoader))  # nosec
        templar_metadata: dict = c.LooseDict(
            {
                "here": rc_file_path.parent,
                "cwd": C.CONTEXT_DIRECTORY,
            }
        )
        templar_env: dict = c.LooseDict(os.environ)
        templar = CommonTemplar(
            metadata=templar_metadata,
            environment=templar_env,
            # Aliases
            meta=templar_metadata,
            env=templar_env,
        )
        rendered_data: t.Dict[str, t.Any] = templar.recursive_render(config_data)
        return from_dict(RC, rendered_data)
