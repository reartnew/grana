"""All bundled action classes"""

from .echo import EchoAction
from .shell import ShellAction
from .subflow import SubflowAction
from .loop import LoopAction

try:
    from .docker_shell import DockerShellAction
except ImportError:  # pragma: no cover
    DockerShellAction = None  # type: ignore
