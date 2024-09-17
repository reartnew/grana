"""All the templating stuff."""

import os
import typing as t

from classlogging import LoggerMixin

from . import containers as c
from .constants import MAX_RECURSION_DEPTH
from .containers import LazyProxy
from .tokenizing import TemplarStringLexer
from ..actions.types import ObjectTemplate, qualify_string_as_potentially_renderable
from ..config.constants import C
from ..exceptions import ActionRenderError, RestrictedBuiltinError, ActionRenderRecursionError

__all__ = [
    "Templar",
]


class Templar(LoggerMixin):
    """Expression renderer"""

    DISABLED_GLOBALS: t.List[str] = ["exec", "eval", "compile", "setattr", "delattr"]

    def __init__(
        self,
        outcomes_map: t.Mapping[str, t.Mapping[str, str]],
        action_states: t.Mapping[str, str],
        context_map: t.Mapping[str, t.Any],
    ) -> None:
        outcomes_leaf_class: t.Type[dict] = (
            c.StrictOutcomeDict if C.STRICT_OUTCOMES_RENDERING else c.LooseDict  # type: ignore
        )
        outcomes_container: c.AttrDict = c.ActionContainingDict(
            {name: outcomes_leaf_class(outcomes_map.get(name, {})) for name in action_states}
        )
        status_container: c.AttrDict = c.ActionContainingDict(action_states)
        context_container: c.AttrDict = c.ContextDict({k: self._load_ctx_node(data=v) for k, v in context_map.items()})
        environment_container: c.AttrDict = c.LooseDict(os.environ)
        self._locals: t.Dict[str, c.AttrDict] = {
            # Full names
            "outcomes": outcomes_container,
            "status": status_container,
            "context": context_container,
            "environment": environment_container,
            # Aliases
            "out": outcomes_container,
            "ctx": context_container,
            "env": environment_container,
        }
        self._globals: t.Dict[str, t.Any] = {
            f: self._make_restricted_builtin_call_shim(f) for f in self.DISABLED_GLOBALS
        }
        self._depth: int = 0

    def render(self, value: str) -> str:
        """Process string data, replacing all @{} occurrences."""
        try:
            return self._internal_render(value)
        except ActionRenderRecursionError as e:
            # Eliminate ActionRenderRecursionError stack trace on hit
            self.logger.debug(f"Rendering {value!r} failed: {e!r}")
            raise ActionRenderError(e) from None
        except ActionRenderError as e:
            self.logger.debug(f"Rendering {value!r} failed: {e!r}", exc_info=True)
            raise

    def _internal_render(self, value: str) -> str:
        """Recursive rendering routine"""
        self._depth += 1
        if self._depth >= MAX_RECURSION_DEPTH:
            # This exception floats to the very "render" call without any logging
            raise ActionRenderRecursionError(f"Recursion depth exceeded: {self._depth}/{MAX_RECURSION_DEPTH}")
        try:
            chunks: t.List[str] = []
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
        self.logger.trace(f"Processing expression: {expression!r}")
        try:
            # pylint: disable=eval-used
            return eval(expression, self._globals, self._locals)  # nosec
        except ActionRenderError:
            raise
        except Exception as e:
            render_failure_source: str = str(e) if isinstance(e, (SyntaxError, NameError)) else repr(e)
            self.logger.warning(f"Expression render failed: {e!r} (for {expression!r})")
            raise ActionRenderError(render_failure_source) from e

    def _evaluate_context_object_expression(self, expression: str) -> t.Any:
        obj: t.Any = self._eval(expression)
        return self._load_ctx_node(obj)

    def _load_ctx_node(self, data: t.Any) -> t.Any:
        """Deep copy of context data,
        while transforming dicts into attribute-accessor proxies
        and turning leaf string values into deferred templates."""
        if isinstance(data, ObjectTemplate):
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
            return c.LazyProxy(lambda: self._internal_render(data))
        return data

    def recursive_render(self, data: t.Any) -> t.Any:
        """Perform recursive rendering"""
        result: t.Any
        if isinstance(data, dict):
            result = {k: self.recursive_render(v) for k, v in data.items()}
        elif isinstance(data, list):
            result = [self.recursive_render(v) for v in data]
        elif isinstance(data, str):
            result = self.render(data)
        elif isinstance(data, ObjectTemplate):
            result = self._eval(data.expression)
        else:
            result = data
        # Unwrap lazy proxies
        if isinstance(result, LazyProxy):
            result = result.__wrapped__
        return result
