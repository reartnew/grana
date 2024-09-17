"""Workflow loaders public methods tests"""

import typing as t
from pathlib import Path

import pytest

from grana.exceptions import LoadError
from grana.loader.base import AbstractBaseWorkflowLoader
from grana.loader.default import DefaultYAMLWorkflowLoader
from grana.loader.helpers import get_default_loader_class_for_source


def test_workflow_load_over_sample(
    sample_workflow: t.Tuple[Path, t.Optional[t.Type[Exception]], t.Optional[str]]
) -> None:
    """Check different variations of good/bad workflows"""
    workflow_path, maybe_exception, maybe_match = sample_workflow
    loader_class: t.Type[AbstractBaseWorkflowLoader] = get_default_loader_class_for_source(workflow_path)
    # Check good workflow
    if maybe_exception is None:
        loader_class().load(workflow_path)
        return
    # Check bad workflow
    with pytest.raises(maybe_exception, match=maybe_match):
        loader_class().load(workflow_path)


def test_yaml_loads() -> None:
    """Test normal YAML loading from a string"""
    DefaultYAMLWorkflowLoader().loads(
        """---
actions:
  - name: RunSomeTool
    type: shell
    description: Run some tool
    command: sometool -c dummy.yml
"""
    )


def test_yaml_loads_bad_structure() -> None:
    """Test bad YAML loading from a string"""
    with pytest.raises(LoadError):
        DefaultYAMLWorkflowLoader().loads(
            """---
actions:
  - {}
"""
        )
