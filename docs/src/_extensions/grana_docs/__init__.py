from sphinx.application import Sphinx

from .strategies import GranaDefaultStrategyDirective, GranaStrategiesListDirective


def setup(app: Sphinx) -> None:
    app.add_directive("grana-default-strategy", GranaDefaultStrategyDirective)
    app.add_directive("grana-strategies-list", GranaStrategiesListDirective)
