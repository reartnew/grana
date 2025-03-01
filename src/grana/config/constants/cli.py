"""CLI options"""

import functools
import typing as t

import click

__all__ = [
    "cli_opts_receiver",
    "get_cli_option",
]

_CLI_OPTIONS: dict[str, t.Any] = {}


def cli_opts_receiver(func):
    """Store CLI options in the _CLI_OPTIONS container for further processing"""

    @functools.wraps(func)
    # pylint: disable=unused-argument
    def wrapped(ctx: click.Context, **kwargs):
        old_cli_options: dict[str, t.Any] = _CLI_OPTIONS.copy()
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
            _CLI_OPTIONS.update(old_cli_options)

    return click.pass_context(wrapped)


def get_cli_option(name: str) -> t.Any:
    """Obtain previously registered CLI option"""
    return _CLI_OPTIONS.get(name)
