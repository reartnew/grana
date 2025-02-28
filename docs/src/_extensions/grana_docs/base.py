from docutils import nodes
from sphinx.util.docutils import SphinxDirective

__all__ = [
    "GranaBaseDirective",
]


class GranaBaseDirective(SphinxDirective):
    has_content = True

    def get_raw_text(self) -> str:
        raise NotImplementedError

    def run(self) -> list[nodes.Node]:
        return self.parse_text_to_nodes(
            self.get_raw_text(),
            allow_section_headings=True,
        )
