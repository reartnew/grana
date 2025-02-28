from sphinx.application import Sphinx

from .strategies import GranaStrategiesDirective


def setup(app: Sphinx) -> None:
    app.add_directive("grana-strategies", GranaStrategiesDirective)
