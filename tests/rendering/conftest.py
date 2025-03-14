# pylint: disable=redefined-outer-name
"""Templar fixtures"""

import typing as t

import pytest

from grana.config.constants import C
from grana.rendering import WorkflowTemplar


@pytest.fixture
def templar_factory(monkeypatch: pytest.MonkeyPatch) -> t.Callable[[dict], WorkflowTemplar]:
    """Prepare a standalone templar"""
    monkeypatch.setenv("TEMPLAR_ENVIRONMENT_KEY", "test")

    def make(locals_map: dict):
        return WorkflowTemplar(
            outcomes_map={
                "Foo": {
                    "bar": "ok",
                    "baz qux.fred": "also ok",
                },
            },
            action_states={"Foo": "SUCCESS"},
            locals_map=locals_map,
            context_map={
                "plugh": "xyzzy",
                "waldo": "@{context.thud}",
                "thud": "@{environment.TEMPLAR_ENVIRONMENT_KEY}",
                "intval": 10,
                "cycle_1": "@{context.cycle_2}",
                "cycle_2": "@{context.cycle_1}",
                "dictData": [
                    {
                        "a": "b",
                    }
                ],
                "deepRenderData": {
                    "foo": "This is a @{context.waldo}",
                    "bar": ["a", "@{context.intval * 2}"],
                    "baz": "@{context.missingStuff}",
                },
            },
        )

    return make


@pytest.fixture
def loose_templar(
    templar_factory: t.Callable[[dict], WorkflowTemplar],
    monkeypatch: pytest.MonkeyPatch,
) -> WorkflowTemplar:
    """Loose templar"""
    monkeypatch.setattr(C, "STRICT_OUTCOMES_RENDERING", False)
    return templar_factory({})


@pytest.fixture
def strict_templar(templar_factory: t.Callable[[dict], WorkflowTemplar]) -> WorkflowTemplar:
    """Strict (default) templar"""
    return templar_factory({})
