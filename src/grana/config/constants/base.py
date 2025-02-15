"""Lazy-loaded constants base machinery"""

import enum
import functools
import os
import typing as t
from pathlib import Path

from . import workflow
from .cli import get_cli_arg
from .rc import RC, sentinel
from ...logging import WithLogger

__all__ = [
    "Inapplicable",
    "ConstantSource",
    "ConstantValueInfo",
    "ConstantBase",
    "CONSTANT_GLOBAL_SOURCES",
]

VT = t.TypeVar("VT")


class Inapplicable(BaseException):
    """Used to indicate that the source can not be used"""


class ConstantSource(enum.Enum):
    """Enumeration of constant effective value sources"""

    WORKFLOW = "workflow configuration"
    COMMAND = "CLI argument"
    ENVIRONMENT = "environment variable"
    CONFIG = "configuration file"
    DEFAULT = "default value"


CONSTANT_GLOBAL_SOURCES: dict[str, ConstantSource] = {}


class ConstantValueInfo(t.NamedTuple):
    """Constants value information"""

    name: str
    value: str
    effective_source: ConstantSource


class ConstantBase(WithLogger, t.Generic[VT]):
    """Constants used in grana runtime"""

    @classmethod
    def cache_clear(cls) -> None:
        """Reset cache"""
        cls._get_global.cache_clear()
        RC.build.cache_clear()

    def __init__(self) -> None:
        self._name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    # Indefinite cache size, so all constants fit into it
    # pylint: disable=method-cache-max-size-none
    @functools.lru_cache(None)
    def _get_global(self) -> VT:
        for source, method in (
            (ConstantSource.COMMAND, self.from_cli_arg),
            (ConstantSource.ENVIRONMENT, self.from_env),
            (ConstantSource.CONFIG, self.from_rc_file),
            (ConstantSource.DEFAULT, self.default),
        ):
            try:
                result = method()
            except Inapplicable:
                pass
            else:
                self.logger.debug(f"Effective global value for {self._name!r} is {result!r} (from {source.value})")
                CONSTANT_GLOBAL_SOURCES[self._name] = source
                return result
        raise Inapplicable

    def _get_local(self) -> VT:
        source: ConstantSource = ConstantSource.WORKFLOW
        result: VT = self.from_workflow_configuration()
        self.logger.debug(f"Effective local value for {self._name!r} is {result!r} (from {source.value})")
        return result

    def __get__(self, instance: t.Any, owner: type) -> VT:
        try:
            return self._get_local()
        except Inapplicable:
            pass
        try:
            return self._get_global()
        except Inapplicable:
            pass
        raise NotImplementedError

    def _get_rc_value(self, name: str) -> t.Any:
        cfg: RC = RC.build()
        value: t.Any = getattr(cfg, name)
        if value is sentinel:
            raise Inapplicable
        return value

    def _get_cli_arg(self, name: str) -> t.Any:
        if (value := get_cli_arg(name)) is None:
            raise Inapplicable
        self.logger.debug(f"Defined CLI argument {name!r} is accessed by {self._name!r}")
        return value

    def _get_wf_config_value(self, name: str) -> t.Any:
        ctx_values_map: dict[str, t.Any] = workflow.CONTEXT_HOLDER.get()
        if name not in ctx_values_map:
            raise Inapplicable
        value: t.Any = ctx_values_map[name]
        self.logger.debug(f"Defined workflow configuration value {name!r} is accessed by {self._name!r}")
        return value

    def _get_env(self, name: str) -> str:
        if (value := os.environ.get(name)) is None:
            raise Inapplicable
        self.logger.debug(f"Defined environment variable {name!r} is accessed by {self._name!r}")
        return value

    @classmethod
    def _string_to_bool(cls, value: str) -> bool:
        """Converts a string value to a boolean"""
        if value == "Y":
            return True
        if value == "N":
            return False
        if value == "":
            raise Inapplicable
        raise ValueError(f"{value!r} is not a valid value for a boolean variable. Expected one of: 'Y', 'N'.")

    @classmethod
    def _string_to_path_list(cls, value: str) -> list[Path]:
        return [Path(item.strip()) for item in value.split(":") if item]

    def from_workflow_configuration(self) -> VT:
        """Try to load the value from loaded workflow configuration variables"""
        raise Inapplicable

    def from_cli_arg(self) -> VT:
        """Try to load the value from CLI args"""
        raise Inapplicable

    def from_env(self) -> VT:
        """Try to load the value from environment variables"""
        raise Inapplicable

    def from_rc_file(self) -> VT:
        """Try to load the value from the RC file"""
        raise Inapplicable

    def default(self) -> VT:
        """Default value to be applied after every other source has been tested"""
        raise Inapplicable
