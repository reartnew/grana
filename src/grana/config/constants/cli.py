"""CLI arguments"""

import functools
import typing as t

import click

__all__ = [
    "cliargs_receiver",
    "get_cli_option",
]

_CLI_OPTIONS: dict[str, t.Any] = {}


def cliargs_receiver(func):
    """Store CLI args in the _CLI_PARAMS container for further processing"""

    @functools.wraps(func)
    # pylint: disable=unused-argument
    def wrapped(ctx: click.Context, **kwargs):
        old_cli_params: dict[str, t.Any] = _CLI_OPTIONS.copy()
        current_ctx: t.Optional[click.Context] = ctx
        while current_ctx:
            for k, v in current_ctx.params.items():
                if k not in _CLI_OPTIONS:
                    _CLI_OPTIONS[k] = v
            current_ctx = current_ctx.parent
        try:
            return func()
        finally:
            # Restore CLI params container
            for k in list(_CLI_OPTIONS):
                del _CLI_OPTIONS[k]
            _CLI_OPTIONS.update(old_cli_params)

    return click.pass_context(wrapped)


def get_cli_option(name: str, *, valid_values: t.Optional[t.Iterable[str]] = None) -> t.Any:
    """Obtain previously registered CLI option"""

    value: t.Any = _CLI_OPTIONS.get(name)
    if valid_values is not None and value is not None and value not in valid_values:
        raise ValueError(
            f"Unrecognized value for the {name!r} option: {value!r}. " f"Expected one of: {sorted(valid_values)}"
        )
    return value
