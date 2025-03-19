"""All the templating stuff."""

from __future__ import annotations

import os
import pathlib
import typing as t

from . import containers as c
from .constants import MAX_RECURSION_DEPTH
from .tokenizing import TemplarStringLexer
from ..actions.types import Expression, qualify_string_as_potentially_renderable, ActionStatus
from ..exceptions import (
    ActionRenderError,
    RestrictedBuiltinError,
    ActionRenderRecursionError,
    PendingActionUnresolvedOutcomeError,
)
from ..logging import WithLogger

__all__ = [
    "CommonTemplar",
    "WorkflowTemplar",
]


class CommonTemplar(WithLogger):
    """Expression renderer"""

    DISABLED_GLOBALS: list[str] = ["exec", "eval", "compile", "setattr", "delattr"]

    def __init__(self, **args: dict[str, t.Any]) -> None:
        self._locals: dict[str, t.Any] = args
        self._globals: dict[str, t.Any] = {f: self._make_restricted_builtin_call_shim(f) for f in self.DISABLED_GLOBALS}
        self._depth: int = 0

    @classmethod
    def _make_base_templar_with_meta_and_env(cls, extra_meta: t.Optional[dict[str, t.Any]] = None) -> CommonTemplar:
        from ..config.constants import C

        meta_dict: dict = c.LooseDict(cwd=C.CONTEXT_DIRECTORY)
        if extra_meta is not None:
            meta_dict.update(extra_meta)
        env_dict: dict = c.LooseDict(os.environ)
        return cls(
            metadata=meta_dict,
            environment=env_dict,
            # Aliases
            meta=meta_dict,
            env=env_dict,
        )

    @classmethod
    def from_source_file(cls, path: pathlib.Path) -> CommonTemplar:
        """Construct a base templar from the source file path"""
        resolved_path: pathlib.Path = path.resolve()
        return cls._make_base_templar_with_meta_and_env(
            extra_meta={
                "source_file": resolved_path,
                "here": resolved_path.parent,
            }
        )

    @classmethod
    def from_context_directory(cls) -> CommonTemplar:
        """Construct a base templar from the source file path"""
        from ..config.constants import C

        return cls._make_base_templar_with_meta_and_env(
            extra_meta={
                "here": C.CONTEXT_DIRECTORY,
            }
        )

    def _render_string(self, value: str) -> str:
        """Process string data, replacing all @{} occurrences."""
        try:
            return self._internal_render_string(value)
        except ActionRenderRecursionError as e:
            # Eliminate ActionRenderRecursionError stack trace on hit
            self.logger.debug(f"Rendering {value!r} failed: {e!r}")
            raise ActionRenderError(e) from None
        except PendingActionUnresolvedOutcomeError:
            # Do not trace PendingActionUnresolvedOutcomeError
            raise
        except ActionRenderError as e:
            self.logger.debug(f"Rendering {value!r} failed: {e!r}", exc_info=True)
            raise

    def _internal_render_string(self, value: str) -> str:
        """Recursive rendering routine"""
        self._depth += 1
        if self._depth >= MAX_RECURSION_DEPTH:
            # This exception floats to the very "render" call without any logging
            raise ActionRenderRecursionError(f"Recursion depth exceeded: {self._depth}/{MAX_RECURSION_DEPTH}")
        try:
            chunks: list[str] = []
            # Cheap check
            if not qualify_string_as_potentially_renderable(value):
                return value
            for lexeme_type, lexeme_value in TemplarStringLexer(value):
                if lexeme_type == TemplarStringLexer.EXPRESSION:
                    lexeme_value = str(self._eval(expression=lexeme_value))
                chunks.append(lexeme_value)
            return "".join(chunks)
        finally:
            self._depth -= 1

    @classmethod
    def _make_restricted_builtin_call_shim(cls, name: str) -> t.Callable:
        def _call(*args, **kwargs) -> t.NoReturn:
            raise RestrictedBuiltinError(name)

        return _call

    def _eval(self, expression: str) -> t.Any:
        """Safely evaluate an expression."""
        self.logger.debug(f"Processing expression: {expression!r}")
        try:
            # pylint: disable=eval-used
            return eval(expression, self._globals, self._locals)  # nosec
        except ActionRenderError:
            raise
        except Exception as e:
            render_failure_source: str = str(e) if isinstance(e, (SyntaxError, NameError)) else repr(e)
            self.logger.warning(f"Expression render failed: {e!r} (for {expression!r})")
            raise ActionRenderError(render_failure_source) from e

    def render(self, data: t.Any) -> t.Any:
        """Perform recursive rendering"""
        result: t.Any
        if isinstance(data, dict):
            result = {k: self.render(v) for k, v in data.items()}
        elif isinstance(data, list):
            result = [self.render(v) for v in data]
        elif isinstance(data, str):
            result = self._render_string(data)
        elif isinstance(data, Expression):
            evaluated_expression: t.Any = self._eval(data.expression)
            result = self.render(evaluated_expression)
        else:
            result = data
        # Unwrap lazy proxies
        while isinstance(result, c.LazyProxy):
            result = result.__wrapped__
        return result


class WorkflowTemplar(CommonTemplar):
    """Expression renderer specifically for workflows"""

    def __init__(
        self,
        *,
        outcomes_map: t.Mapping[str, t.Mapping[str, str]],
        action_states: t.Mapping[str, str],
        context_map: t.Mapping[str, t.Any],
        locals_map: t.Mapping[str, t.Any],
        metadata: t.Optional[t.Mapping[str, t.Any]] = None,
    ) -> None:
        outcomes_container: c.AttrDict = c.ActionOutcomeAggregateDict()
        for name, status_str in action_states.items():
            action_outcomes: t.Optional[dict] = None
            if status_str not in (ActionStatus.PENDING.value, ActionStatus.RUNNING.value):
                action_outcomes = c.OutcomeDict(outcomes_map.get(name, {}))
            outcomes_container[name] = action_outcomes
        status_container: c.AttrDict = c.ActionContainingDict(action_states)
        context_container: c.AttrDict = c.AttrDict({k: self._load_ctx_node(data=v) for k, v in context_map.items()})
        locals_container: c.AttrDict = c.AttrDict({k: self._load_ctx_node(data=v) for k, v in locals_map.items()})
        environment_container: c.AttrDict = c.LooseDict(os.environ)
        metadata_container: c.AttrDict = c.LooseDict({"status": status_container})
        if metadata is not None:
            metadata_container.update(metadata)
        super().__init__(
            # Full names
            outcomes=outcomes_container,
            context=context_container,
            environment=environment_container,
            locals=locals_container,
            metadata=metadata_container,
            # Aliases
            out=outcomes_container,
            ctx=context_container,
            env=environment_container,
            loc=locals_container,
            meta=metadata_container,
        )

    def _evaluate_context_object_expression(self, expression: str) -> t.Any:
        obj: t.Any = self._eval(expression)
        return self._load_ctx_node(obj)

    def _load_ctx_node(self, data: t.Any) -> t.Any:
        """Deep copy of context data,
        while transforming dicts into attribute-accessor proxies
        and turning leaf string values into deferred templates."""
        if isinstance(data, Expression):
            return c.LazyProxy(lambda: self._evaluate_context_object_expression(data.expression))
        if isinstance(data, dict):
            result_dict = c.AttrDict()
            for key, value in data.items():
                result_dict[key] = self._load_ctx_node(value)
            return result_dict
        if isinstance(data, list):
            result_list = []
            for item in data:
                result_list.append(self._load_ctx_node(item))
            return result_list
        if isinstance(data, str) and qualify_string_as_potentially_renderable(data):
            return c.LazyProxy(lambda: self._internal_render_string(data))
        return data
