from grana.config.constants import C, base
from .base import GranaBaseDirective
import typing as t

__all__ = [
    "GranaConfigurationParameters",
]


def format_object_doc(obj: t.Any) -> str:
    if obj.__doc__ is None:
        raise ValueError(f"No default doc for {obj!r}")
    return obj.__doc__.replace("\n", " ")


class GranaConfigurationParameters(GranaBaseDirective):

    def get_raw_text(self) -> str:
        data: list[str] = []
        for c in C.constants_info():
            data.append(f"## {c.name}")
            data.append(":::{list-table}")
            data.append(":widths: 1 2")

            def add_row(header: str, value: t.Any) -> None:
                data.append(f"*   - **{header}**")
                data.append(f"    - {value}")

            def code(value: t.Any) -> str:
                return f"`{value}`"

            defn_class: type[base.ConstantBase] = c.definition.__class__
            add_row("Description", format_object_doc(defn_class))
            if defn_class.WORKFLOW_CONFIG_PARAMETER_NAME is not base.sentinel:
                add_row("Workflow file configuration field", code(defn_class.WORKFLOW_CONFIG_PARAMETER_NAME))
            elif defn_class.from_workflow_configuration.__doc__:
                add_row("Workflow file configuration field", format_object_doc(defn_class.from_workflow_configuration))
            if defn_class.COMMAND_LINE_OPTION_NAME is not base.sentinel:
                add_row("Command-line option", code(f"--{defn_class.COMMAND_LINE_OPTION_NAME.replace('_', '-')}"))
            elif defn_class.from_cli_option.__doc__:
                add_row("Command-line option", format_object_doc(defn_class.from_cli_option))
            if defn_class.ENVIRONMENT_VARIABLE_NAME is not base.sentinel:
                add_row("Environment variable", code(defn_class.ENVIRONMENT_VARIABLE_NAME))
            elif defn_class.from_env.__doc__:
                add_row("Environment variable", format_object_doc(defn_class.from_env))
            if defn_class.RC_PARAMETER_NAME is not base.sentinel:
                add_row("RC file field", code(defn_class.RC_PARAMETER_NAME))
            elif defn_class.from_rc_file.__doc__:
                add_row("RC file field", format_object_doc(defn_class.from_rc_file))
            if defn_class.DEFAULT is not base.sentinel:
                add_row("Default", code(defn_class.DEFAULT))
            else:
                add_row("Default", format_object_doc(defn_class.default))
            data.append(":::")
        return "\n".join(data)
