"""Interactive dialog."""

import sys
import typing as t

try:
    import inquirer  # type: ignore
except ImportError:  # pragma: no cover
    inquirer = None

from ..exceptions import InteractionError

__all__ = [
    "run_dialog",
]


def run_dialog(choices: list[t.Tuple[str, str]], default: list[str]) -> list[str]:  # pragma: no cover
    """Invoke an inquirer dialog"""
    if inquirer is None:
        raise InteractionError("Inquirer is not installed. Try reinstalling grana with the `dialog` or `all` extras.")
    if not sys.stdin.isatty():
        raise InteractionError("Not a TTY")
    answers: dict[str, list[str]] = inquirer.prompt(
        questions=[
            inquirer.Checkbox(
                name="actions",
                message="Select actions (SPACE to check, RETURN to proceed)",
                choices=choices,
                default=default,
                carousel=True,
            )
        ],
        raise_keyboard_interrupt=True,
    )
    selected_action_names: list[str] = answers["actions"]
    return selected_action_names
