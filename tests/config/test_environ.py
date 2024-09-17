"""Environment variables tests"""

import textwrap
import typing as t

import pytest

from grana.config.environment import Env
from grana.tools.inspect import get_class_annotations


@pytest.mark.parametrize("variable_name", list(get_class_annotations(Env)))
def test_env(variable_name: str) -> None:
    """Test that all vars are described in doc"""
    docs_lines: t.List[str] = textwrap.dedent(Env.__doc__).splitlines()  # type: ignore
    assert f"{variable_name}:" in docs_lines, f"Variable {variable_name!r} is not documented"
