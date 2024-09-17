"""All bundled action classes"""

from .echo import EchoAction
from .shell import ShellAction

try:
    from .docker_shell import DockerShellAction
except ImportError:  # pragma: no cover
    DockerShellAction = None  # type: ignore
