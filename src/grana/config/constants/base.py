"""Lazy-loaded constants base machinery"""

import enum
import functools
import os
import typing as t
from pathlib import Path

from . import workflow
from .cli import get_cli_option
from .rc import RC, sentinel
from ...logging import WithLogger

__all__ = [
    "Inapplicable",
    "ConstantSource",
    "ConstantValueInfo",
    "ConstantBase",
    "CONSTANT_GLOBAL_SOURCES",
    "ConstantBool",
    "ConstantPathList",
    "ConstantPath",
]

VT = t.TypeVar("VT")


class Inapplicable(BaseException):
    """Used to indicate that the source can not be used"""


class ConstantSource(enum.Enum):
    """Enumeration of constant effective value sources"""

    WORKFLOW = "workflow configuration"
    COMMAND = "CLI option"
    ENVIRONMENT = "environment variable"
    CONFIG = "configuration file"
    DEFAULT = "default value"


CONSTANT_GLOBAL_SOURCES: dict[str, ConstantSource] = {}


class ConstantValueInfo(t.NamedTuple):
    """Constants value information"""

    name: str
    value: str
    effective_source: ConstantSource


class ConstantSentinelType(str):
    """Sentinel value type for ConstantBase"""


constant_sentinel = ConstantSentinelType()


class ConstantBase(WithLogger, t.Generic[VT]):
    """Constants used in grana runtime"""

    ENVIRONMENT_VARIABLE_NAME: str = constant_sentinel
    COMMAND_LINE_OPTION_NAME: str = constant_sentinel
    RC_PARAMETER_NAME: str = constant_sentinel
    WORKFLOW_CONFIG_PARAMETER_NAME: str = constant_sentinel
    DEFAULT: t.Union[VT, ConstantSentinelType] = constant_sentinel

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
            (ConstantSource.COMMAND, self.from_cli_option),
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

    def cast(self, value: t.Any) -> VT:
        """Transform a value into the desired type"""
        return t.cast(VT, value)

    def from_workflow_configuration(self) -> VT:
        """Try to load the value from loaded workflow configuration variables"""
        wf_cfg_param_name: str = self.WORKFLOW_CONFIG_PARAMETER_NAME
        if wf_cfg_param_name is constant_sentinel:
            raise Inapplicable
        ctx_values_map: dict[str, t.Any] = workflow.CONTEXT_HOLDER.get()
        if wf_cfg_param_name not in ctx_values_map:
            raise Inapplicable
        workflow_config_parameter_value: t.Any = ctx_values_map[wf_cfg_param_name]
        self.logger.debug(f"Defined workflow configuration value {wf_cfg_param_name!r} is accessed by {self._name!r}")
        return self.cast(workflow_config_parameter_value)

    def from_cli_option(self) -> VT:
        """Try to load the value from CLI options"""
        cli_option_name: str = self.COMMAND_LINE_OPTION_NAME
        if cli_option_name is constant_sentinel:
            raise Inapplicable
        if (cli_option_value := get_cli_option(cli_option_name)) is None:
            raise Inapplicable
        self.logger.debug(f"Defined CLI option {cli_option_name!r} is accessed by {self._name!r}")
        return self.cast(cli_option_value)

    def from_env(self) -> VT:
        """Try to load the value from environment variables"""
        env_var_name: str = self.ENVIRONMENT_VARIABLE_NAME
        if env_var_name is constant_sentinel:
            raise Inapplicable
        if (env_var_value := os.environ.get(env_var_name)) is None:
            raise Inapplicable
        self.logger.debug(f"Defined environment variable {env_var_name!r} is accessed by {self._name!r}")
        return self.cast(env_var_value)

    def from_rc_file(self) -> VT:
        """Try to load the value from the RC file"""
        rc_param_name: str = self.RC_PARAMETER_NAME
        if rc_param_name is constant_sentinel:
            raise Inapplicable
        cfg: RC = RC.build()
        rc_param_value: t.Any = getattr(cfg, rc_param_name)
        if rc_param_value is sentinel:
            raise Inapplicable
        return self.cast(rc_param_value)

    def default(self) -> VT:
        """Default value to be applied after every other source has been tested"""
        if isinstance(self.DEFAULT, ConstantSentinelType):
            raise Inapplicable
        return self.DEFAULT


class ConstantBool(ConstantBase[bool]):
    """Base for boolean constants"""

    def cast(self, value: t.Union[str, bool]) -> bool:
        if isinstance(value, bool):
            return value
        if value == "Y":
            return True
        if value == "N":
            return False
        if value == "":
            raise Inapplicable
        raise ValueError(f"{value!r} is not a valid value for a boolean variable. Expected one of: 'Y', 'N'.")


class ConstantPathList(ConstantBase[list[Path]]):
    """Base for path list constants"""

    def cast(self, value: t.Union[str, list[Path]]) -> list[Path]:
        if isinstance(value, str):
            return [Path(item.strip()) for item in value.split(":") if item]
        return value


class ConstantPath(ConstantBase, t.Generic[VT]):
    """Base class for path constants"""

    def cast(self, value: t.Union[str, Path]) -> Path:
        return Path(value)
