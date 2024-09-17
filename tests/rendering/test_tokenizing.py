"""Tokenizer+lexer tests"""

import tokenize
import typing as t

from pytest_data_suites import DataSuite

from grana.rendering.tokenizing import ExpressionTokenizer, TemplarStringLexer


class LexerTestCase(t.TypedDict):
    """Lexer test case variables"""

    source: str
    result: t.List[t.Tuple[int, str]]


class LexerDataSuite(DataSuite):
    """Lexer test cases"""

    plain = LexerTestCase(
        source="foobar",
        result=[(0, "foobar")],
    )
    clean_expression = LexerTestCase(
        source="@{ a.b.c }",
        result=[(1, "a .b .c ")],
    )
    multiple_expressions = LexerTestCase(
        source="@{ a.b.c } @{ a.b.c }",
        result=[(1, "a .b .c "), (0, " "), (1, "a .b .c ")],
    )
    complex_expression = LexerTestCase(
        source="""Hello, @{ {"foo": "world"}["foo"] }!""",
        result=[(0, "Hello, "), (1, '{"foo":"world"}["foo"]'), (0, "!")],
    )
    expression_with_a_newline = LexerTestCase(
        source="@{a.b.c + \n a.b.d}",
        result=[(1, "a .b .c +a .b .d ")],
    )
    shlex_expression = LexerTestCase(
        source='@{ x."y z".w }',
        result=[(1, 'x ."y z".w ')],
    )
    dashes_expression = LexerTestCase(
        source="@{ x-y.z-w }",
        result=[(1, "x -y .z -w ")],
    )
    at_in_the_scalar = LexerTestCase(
        source='"@{ a.b }"',
        result=[(0, '"'), (1, "a .b "), (0, '"')],
    )


@LexerDataSuite.parametrize
def test_lexer(source: str, result: t.List[t.Tuple[int, str]]) -> None:
    """Check lexer result validity"""
    assert list(TemplarStringLexer(source)) == result


def test_tokenizer_eof() -> None:
    """Validate tokenizer EOF suppression"""
    assert [
        token.string
        for token in ExpressionTokenizer("{ foo.bar }{")
        if token.string and token.type != tokenize.ENCODING
    ] == [
        "{",
        "foo",
        ".",
        "bar",
        "}",
        "{",
    ]
