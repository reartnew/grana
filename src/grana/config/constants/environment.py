"""Separate environment-centric module"""

import pathlib

__all__ = [
    "ENV_DOC",
    "to_path_list",
]


def to_path_list(value: str) -> list[pathlib.Path]:
    """Converts a string value to a list of paths according to the same logic as for UNIX `path`"""
    return [pathlib.Path(item.strip()) for item in value.split(":") if item]


ENV_DOC: str = """
    GRANA_LOG_LEVEL:
        Specifies the log level.
        Default is ERROR.
    GRANA_LOG_FILE:
        Specifies the log file.
        Defaults to the standard error stream.
    GRANA_ENV_FILE:
        Which file to load environment variables from. Expected format is k=v.
        Default is .env in the current directory.
    GRANA_WORKFLOW_FILE:
        Workflow file to use.
        Default behaviour is scan the current working directory.
    GRANA_WORKFLOW_LOADER_SOURCE_FILE:
        May point a file containing a WorkflowLoader class definition, which will replace the default implementation.
    GRANA_DISPLAY_NAME:
        Select the display by name from the bundled list.
    GRANA_DISPLAY_SOURCE_FILE:
        May point a file containing a Display class definition, which will replace the default implementation.
    GRANA_STRATEGY_NAME:
        Specifies the execution strategy.
        Default is 'explicit'.
    GRANA_FORCE_COLOR:
        When specified, this will force the colored or non-coloured output, according to the setting.
    GRANA_SHELL_INJECT_YIELD_FUNCTION:
        When set to True, all shell-related actions will inject the yield_outcome function definition.
        Default is True.
    GRANA_EXTERNAL_MODULES_PATHS:
        A colon-separated list of local directories, which are added to the sys.path while loading any external modules.
        Default is an empty list.
    GRANA_ACTIONS_CLASS_DEFINITIONS_DIRECTORY:
        A colon-separated list of local directories, from which all `*.py` files will be considered action definitions.
        Each loaded definition is named after the filename stem and must contain an `Action` class.
        e.g. foo-bar.py may be referenced in a YAML workflow as `type: foo-bar`.
    GRANA_STRICT_OUTCOMES_RENDERING:
        When set to True, rendering a missing outcome key will result in an error instead of an empty string.
        Default is False.
    GRANA_DEFAULT_SHELL_EXECUTABLE:
        Specifies which shell executable should be used by the shell action by default.
        Default is /bin/sh.
    """
