"""Command-line interface entry"""

import functools
import sys
import typing as t
from logging import getLogger

import click

from . import logging as grana_logging
from .config.constants import C, rc
from .config.constants.base import ConstantSource
from .config.constants.cli import get_cli_option, cli_opts_receiver
from .display.color import Color
from .exceptions import BaseError, ExecutionFailed
from .loader.default import DefaultYAMLWorkflowLoader
from .runner import Runner
from .tools.proxy import DeferredCallsProxy
from .version import __version__

logger = DeferredCallsProxy(obj=getLogger(__name__))


class WorkflowPositionalArgument(click.Argument):
    """Optional positional argument for the workflow source"""

    # pylint: disable=unused-argument
    def __init__(self, param_decls: t.Sequence[str], required: t.Optional[bool] = None, **attrs: t.Any) -> None:
        super().__init__(param_decls, required=False, nargs=-1)

    def get_help_record(self, ctx: click.Context) -> t.Optional[t.Tuple[str, str]]:
        return self.make_metavar(), (
            "Workflow source file. When not given, will look for one of grana.yml/grana.yaml "
            "files in the context directory. Use the '-' value to read yaml configuration from the standard input"
        )

    def process_value(self, ctx: click.Context, value: t.Any) -> t.Optional[str]:
        """Check that there is not more than one argument for the workflow source"""
        vanilla_value: t.Tuple[str, ...] = super().process_value(ctx, value)
        if len(vanilla_value) > 1:
            raise click.BadParameter("Cannot apply more than one value", param=self)
        return vanilla_value[0] if vanilla_value else None

    def make_metavar(self) -> str:
        """Fixed representation"""
        return "[WORKFLOW_FILE]"


@click.group
@click.option(
    "-l",
    "--log-level",
    help="Logging subsystem level",
)
@click.option(
    "-L",
    "--log-file",
    help="Log file path",
)
@click.option(
    "-d",
    "--display",
    help="Display name",
)
@cli_opts_receiver
def main() -> None:
    """Open-source command-line task automation tool."""


def wrap_cli_command(func):
    """Standard loading and error handling"""

    @cli_opts_receiver
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        # Enable constants caches
        with C.mount_context_cache():
            grana_logging.configure_logging(
                main_file=C.LOG_FILE,
                level=C.LOG_LEVEL,
                colorize=C.USE_COLOR and not C.LOG_FILE,
            )
            logger.uncork()
            rc.logger.uncork()
            try:
                return func(*args, **kwargs)
            except BaseError as e:
                logger.debug("", exc_info=True)
                sys.stderr.write(f"! {e}\n")
                sys.exit(e.CODE)
            except ExecutionFailed:
                logger.debug("Some steps failed")
                sys.exit(1)
            except Exception as e:
                logger.debug("", exc_info=True)
                sys.stderr.write(f"! UNHANDLED EXCEPTION: {e!r}\n")
                sys.exit(2)

    return wrapped


@main.command
@wrap_cli_command
@click.option(
    "-s",
    "--strategy",
    help="Execution strategy for the workflow",
)
@click.option("-i", "--interactive", help="Run in dialog mode.", is_flag=True, default=False)
@click.argument("workflow_file", cls=WorkflowPositionalArgument, help="Workflow file path")
def run() -> None:
    """Run the pipeline."""
    Runner().run_sync()


@main.command
@wrap_cli_command
@click.argument("workflow_file", cls=WorkflowPositionalArgument)
def validate() -> None:
    """Check workflow source validity.
    Return code is zero, when validation passes."""
    action_num: int = len(Runner().workflow)
    logger.info(f"Located actions number: {action_num}")


@main.command
@wrap_cli_command
def version() -> None:
    """Display package version."""
    print(__version__)


@main.group
def info() -> None:
    """Miscellaneous tool information."""


@info.command
def env_vars() -> None:
    """Shows environment variables names that are taken into account."""
    print(C.env_doc())


@info.command
@wrap_cli_command
@click.option("--show-defaults", help="Show constants with default values", is_flag=True, default=False)
def runtime() -> None:
    """Shows runtime information."""
    display_spool: list[str] = []

    def section(name: str) -> None:
        display_spool.append(f"\n{Color.bold(name)}")

    def mapping(name: str) -> None:
        display_spool.append(f"{Color.yellow(name)}:")

    def kv(k: str, v: t.Any, *, indent: int = 0) -> None:
        display_spool.append(f"{'    ' * indent}{Color.blue(k)}: {Color.green(str(v))}")

    section("Python")
    kv("Version", sys.version.split(" ", 1)[0])
    kv("Executable", sys.executable)

    section("Configuration")
    for const_descriptor in C.constants_info():
        if const_descriptor.effective_source == ConstantSource.DEFAULT and not get_cli_option("show_defaults"):
            continue
        mapping(const_descriptor.name)
        kv("Value", const_descriptor.value, indent=1)
        kv("Source", const_descriptor.effective_source.name.lower(), indent=1)

    section("Actions")
    for actions_name, (action_class, action_source) in sorted(
        DefaultYAMLWorkflowLoader().get_action_factories_info().items()
    ):
        mapping(actions_name)
        if doc := getattr(action_class, "__doc__", ""):
            kv("Info", doc, indent=1)
        kv("Source", action_source, indent=1)

    d = C.INTERNAL_DISPLAY_CLASS()
    for line in display_spool:
        d.display(line)
