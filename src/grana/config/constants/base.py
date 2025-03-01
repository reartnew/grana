"""Lazy-loaded constants base machinery"""

from __future__ import annotations

import dataclasses
import enum
import os
import typing as t
from pathlib import Path

from . import workflow, rc
from .cache import CACHE
from .cli import get_cli_option
from ...logging import WithLogger
from ...rendering.containers import LazyProxy

__all__ = [
    "Inapplicable",
    "ConstantSource",
    "ConstantBase",
    "ConstantProxyDescriptor",
    "ConstantBool",
    "ConstantPathList",
    "ConstantPath",
    "sentinel",
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
    MULTIPLE = "multiple sources"


@dataclasses.dataclass
class ConstantProxyDescriptor:
    """Descriptor for constant values"""

    name: str
    value: t.Any
    definition: t.Any
    effective_source: ConstantSource

    def __call__(self) -> t.Any:
        return self.value


class ConstantSentinelType(str):
    """Sentinel value type for ConstantBase"""


sentinel = ConstantSentinelType()


# pylint: disable=missing-function-docstring
class ConstantBase(WithLogger, t.Generic[VT]):
    """Constants used in grana runtime"""

    ENVIRONMENT_VARIABLE_NAME: str = sentinel
    COMMAND_LINE_OPTION_NAME: str = sentinel
    RC_PARAMETER_NAME: str = sentinel
    WORKFLOW_CONFIG_PARAMETER_NAME: str = sentinel
    DEFAULT: t.Union[VT, ConstantSentinelType] = sentinel

    def __init__(self) -> None:
        self._name: str = ""
        self._result_and_source: t.Union[tuple[VT, ConstantSource], ConstantSentinelType] = sentinel

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def _register_result(self, result: VT, source: ConstantSource) -> None:
        if self._result_and_source is sentinel:
            self.logger.debug(f"{self._name} is accepted from {source}")
            self._result_and_source = result, source

    def __get__(self, instance: t.Any, owner: type) -> VT:
        return self.get()

    @CACHE.wrap
    def get(self) -> VT:
        """To be cached in the context"""
        self._result_and_source = sentinel
        for source, method in (
            (ConstantSource.WORKFLOW, self.from_workflow_configuration),
            (ConstantSource.COMMAND, self.from_cli_option),
            (ConstantSource.ENVIRONMENT, self.from_env),
            (ConstantSource.CONFIG, self.from_rc_file),
            (ConstantSource.DEFAULT, self.default),
        ):
            try:
                result = method()
            except Inapplicable:
                continue
            except Exception as e:
                self.logger.warning(f"Evaluating {self._name!r} from {source.value} failed: {e!r}")
                raise
            self._register_result(result=result, source=source)
        if isinstance(self._result_and_source, ConstantSentinelType):
            raise NotImplementedError
        effective_result, effective_source = self._result_and_source
        self.logger.info(f"Effective value for {self._name!r} is {effective_result!r} (from {effective_source.value})")
        return t.cast(
            VT,
            LazyProxy(
                ConstantProxyDescriptor(
                    name=self._name,
                    value=effective_result,
                    definition=self,
                    effective_source=effective_source,
                )
            ),
        )

    def cast(self, value: t.Any) -> VT:
        """Transform a value into the desired type"""
        return t.cast(VT, value)

    def from_workflow_configuration(self) -> VT:
        # Try to load the value from loaded workflow configuration variables
        wf_cfg_param_name: str = self.WORKFLOW_CONFIG_PARAMETER_NAME
        if wf_cfg_param_name is sentinel:
            raise Inapplicable
        ctx_values_map: dict[str, t.Any] = workflow.CONTEXT_HOLDER.get()
        if wf_cfg_param_name not in ctx_values_map:
            raise Inapplicable
        workflow_config_parameter_value: t.Any = ctx_values_map[wf_cfg_param_name]
        self.logger.debug(f"Defined workflow configuration value {wf_cfg_param_name!r} is accessed by {self._name!r}")
        return self.cast(workflow_config_parameter_value)

    def from_cli_option(self) -> VT:
        # Try to load the value from CLI options
        cli_option_name: str = self.COMMAND_LINE_OPTION_NAME
        if cli_option_name is sentinel:
            raise Inapplicable
        if (cli_option_value := get_cli_option(cli_option_name)) is None:
            raise Inapplicable
        self.logger.debug(f"Defined CLI option {cli_option_name!r} is accessed by {self._name!r}")
        return self.cast(cli_option_value)

    def from_env(self) -> VT:
        # Try to load the value from environment variables
        env_var_name: str = self.ENVIRONMENT_VARIABLE_NAME
        if env_var_name is sentinel:
            raise Inapplicable
        if (env_var_value := os.environ.get(env_var_name)) is None:
            raise Inapplicable
        self.logger.debug(f"Defined environment variable {env_var_name!r} is accessed by {self._name!r}")
        return self.cast(env_var_value)

    def from_rc_file(self) -> VT:
        # Try to load the value from the RC file
        rc_param_name: str = self.RC_PARAMETER_NAME
        if rc_param_name is sentinel:
            raise Inapplicable
        cfg: rc.RC = rc.RC.build()
        rc_param_value: t.Any = getattr(cfg, rc_param_name)
        if rc_param_value is rc.sentinel:
            raise Inapplicable
        return self.cast(rc_param_value)

    def default(self) -> VT:
        # Default value to be applied after every other source has been tested
        if isinstance(self.DEFAULT, ConstantSentinelType):
            raise Inapplicable  # pragma: no cover
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

    def _register_result(self, result: list[Path], source: ConstantSource) -> None:
        """Cumulative constant processing"""
        if self._result_and_source is not sentinel:
            prev_result, _ = self._result_and_source
            result += prev_result  # type: ignore[arg-type]
            source = ConstantSource.MULTIPLE
        self._result_and_source = result, source

    def cast(self, value: t.Union[str, list[Path]]) -> list[Path]:
        if isinstance(value, str):
            return [Path(item.strip()) for item in value.split(":") if item]
        return value

    def default(self) -> list[Path]:
        """An empty list"""
        return []


class ConstantPath(ConstantBase, t.Generic[VT]):
    """Base class for path constants"""

    def cast(self, value: t.Union[str, Path]) -> Path:
        return Path(value)
