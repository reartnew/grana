from sphinx.application import Sphinx

from .base import GranaBaseDirective
from . import (
    strategies,
    configuration,
)


def setup(app: Sphinx) -> None:
    for directive_class in (
        strategies.GranaDefaultStrategy,
        strategies.GranaStrategiesList,
        configuration.GranaConfigurationParameters,
    ):  # type: type[GranaBaseDirective]
        app.add_directive(directive_class.get_directive_name(), directive_class)
