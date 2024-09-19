"""Templar tests"""

import re

import pytest

from grana.exceptions import ActionRenderError
from grana.rendering import Templar


def test_outcome_rendering(loose_templar: Templar) -> None:
    """Test outcome rendering"""
    assert loose_templar.render("@{outcomes.Foo.bar}") == "ok"


def test_outcome_missing_action_rendering(loose_templar: Templar) -> None:
    """Test missing action outcome rendering"""
    with pytest.raises(ActionRenderError, match="Action not found"):
        loose_templar.render("@{outcomes.unknown_action.bar}")


def test_strict_outcome_missing_key_rendering(strict_templar: Templar) -> None:
    """Test missing outcome key rendering"""
    with pytest.raises(ActionRenderError, match="Outcome key 'unknown key' not found"):
        strict_templar.render("@{outcomes.Foo['unknown key']}")


def test_status_rendering(loose_templar: Templar) -> None:
    """Test status rendering"""
    assert loose_templar.render("@{status.Foo}") == "SUCCESS"


def test_status_missing_action_rendering(loose_templar: Templar) -> None:
    """Test status missing action rendering"""
    with pytest.raises(ActionRenderError, match="Action not found"):
        loose_templar.render("@{status['Unknown action']}")


def test_environment_rendering(loose_templar: Templar) -> None:
    """Test environment rendering"""
    assert loose_templar.render("@{environment.TEMPLAR_ENVIRONMENT_KEY}") == "test"
    assert loose_templar.render("@{environment.TEMPLAR_ENVIRONMENT_KEY_UNSET}") == ""


def test_context_rendering(loose_templar: Templar) -> None:
    """Test context rendering"""
    assert loose_templar.render("@{context.plugh}") == "xyzzy"


def test_context_missing_key_rendering(loose_templar: Templar) -> None:
    """Test context missing key rendering"""
    with pytest.raises(ActionRenderError, match="Context key not found"):
        loose_templar.render("@{context.unknown_key}")


def test_unknown_expression_type_rendering(loose_templar: Templar) -> None:
    """Test unknown expression type rendering"""
    with pytest.raises(ActionRenderError, match="name 'unknown_type' is not defined"):
        loose_templar.render("@{unknown_type.unknown_key}")


def test_at_sign_escape_rendering(loose_templar: Templar) -> None:
    """Test '@' sign escaping"""
    assert loose_templar.render("@@{outcomes.Foo.bar}") == "@@{outcomes.Foo.bar}"


def test_complex_expression_split_rendering(loose_templar: Templar) -> None:
    """Test complex expression rendering"""
    assert loose_templar.render("@{outcomes.Foo['baz qux.fred']}") == "also ok"


def test_loose_rendering(loose_templar: Templar) -> None:
    """Test loose rendering"""
    assert loose_templar.render("@{outcomes.Foo.unknown_key}") == ""


def test_restricted_exec(loose_templar: Templar) -> None:
    """Test exec rendering"""
    with pytest.raises(ActionRenderError, match=re.escape("RestrictedBuiltinError('exec')")):
        loose_templar.render("@{exec('import sys')}")


def test_restricted_setattr(loose_templar: Templar) -> None:
    """Test setattr rendering"""
    with pytest.raises(ActionRenderError, match=re.escape("RestrictedBuiltinError('setattr')")):
        loose_templar.render("@{setattr(status, 'Foo', 'SUCCESS')}")


def test_complex_rendering(loose_templar: Templar) -> None:
    """Test complex expression rendering"""
    assert (
        loose_templar.render('@{ f"{context.intval ** 2} percents of actions finished" }: @{dict(status)}')
        == "100 percents of actions finished: {'Foo': 'SUCCESS'}"
    )


def test_expression_with_spaces(loose_templar: Templar) -> None:
    """Test expression with space rendering"""
    assert loose_templar.render("@{ 'OK' if str(context.plugh) == 'xyzzy' else 'Not OK' }") == "OK"


def test_recursive_expression(loose_templar: Templar) -> None:
    """Test expression with nesting"""
    assert loose_templar.render("@{ context.waldo }") == "test"


def test_cycle_expression(loose_templar: Templar) -> None:
    """Test expression with cycle"""
    with pytest.raises(ActionRenderError, match="Recursion depth exceeded"):
        loose_templar.render("@{ context.cycle_1 }")


def test_dict_context_expression_getitem(loose_templar: Templar) -> None:
    """Test dict context expression via __getitem__"""
    assert loose_templar.render("@{ context.dictData[0]['a'] }") == "b"


def test_dict_context_expression_getattr(loose_templar: Templar) -> None:
    """Test dict context expression via __getattr__"""
    assert loose_templar.render("@{ context.dictData[0].a }") == "b"


def test_render_non_string_object(loose_templar: Templar) -> None:
    """Test rendering of the whole complex object"""
    assert loose_templar.render("@{ context.dictData }-@{ context.intval }") == "[{'a': 'b'}]-10"


def test_render_deep_context(loose_templar: Templar) -> None:
    """Test rendering of deep context references"""
    assert loose_templar.render("@{ context.deepRenderData.foo }") == "This is a test"
    assert loose_templar.render("@{ context.deepRenderData.bar }") == "['a', '20']"
