"""All the templating stuff."""

import io
import tokenize
import typing as t

__all__ = [
    "ExpressionTokenizer",
    "TemplarStringLexer",
]


class ExpressionTokenizer:
    """Utilize tokenize.tokenize while simultaneously tracking the caret position"""

    def __init__(self, data: str) -> None:
        self._bytes: bytes = data.encode()
        self._stream: io.BytesIO = io.BytesIO(self._bytes)
        self._token_generator: t.Iterator[tokenize.TokenInfo] = self._careless_tokenize()
        self._scanned_lines_length_sum: int = 0
        self._prev_line_length: int = 0
        self.position: int = 0

    def _readline(self) -> bytes:
        """Memorize read lines length sum"""
        line: bytes = self._stream.readline()
        self._scanned_lines_length_sum += self._prev_line_length
        self._prev_line_length = len(line)
        return line

    def _careless_tokenize(self) -> t.Generator[tokenize.TokenInfo, None, None]:
        """Tokenize the stream, while ignoring all `TokenError`s"""
        try:
            yield from tokenize.tokenize(self._readline)
        except tokenize.TokenError:
            pass

    def get_token(self) -> tokenize.TokenInfo:
        """Yield a token and memorize its original position"""
        token: tokenize.TokenInfo = next(self._token_generator)
        self.position = self._scanned_lines_length_sum + token.start[1]
        return token

    def __iter__(self) -> t.Iterator[tokenize.TokenInfo]:
        return self

    def __next__(self) -> tokenize.TokenInfo:
        return self.get_token()


class TemplarStringLexer:
    """Emit raw text and expressions separately"""

    TEXT: int = 0
    EXPRESSION: int = 1
    _IGNORED_TOKENS_TYPES = [
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.ENCODING,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
    ]

    def __init__(self, data: str) -> None:
        self._data: str = data
        self._len: int = len(data)
        self._caret: int = 0

    def _get_symbol(self) -> str:
        """Read the next symbol of the input data"""
        if self._caret >= self._len:
            raise EOFError
        self._caret += 1
        return self._data[self._caret - 1]

    def __iter__(self) -> t.Iterator[t.Tuple[int, str]]:
        """Alternately yield raw text to leave as is and expressions to evaluate"""
        armed_at: bool = False
        text_start: int = self._caret
        while True:
            try:
                # Each expression starts with an "@{" pair, which can be escaped by doubling the "@" down,
                # thus each second "@" disengages the expression scanning readiness
                if (symbol := self._get_symbol()) == "@":
                    armed_at = not armed_at
                    continue
                if symbol == "{" and armed_at:
                    if maybe_text := self._data[text_start : self._caret - 2]:  # -2 stands for the "@{"
                        yield self.TEXT, maybe_text
                    expression_source_length, expression = self._read_expression()
                    yield self.EXPRESSION, expression
                    text_start = self._caret + expression_source_length + 1  # Start again right after the closing brace
                armed_at = False
            except (StopIteration, EOFError):
                if maybe_text := self._data[text_start:]:
                    yield self.TEXT, maybe_text
                break

    def _read_expression(self) -> t.Tuple[int, str]:
        """Use a tokenizer to detect the closing brace"""
        brace_depth: int = 0
        collected_tokens: t.List[t.Tuple[int, str]] = []
        tokenizer = ExpressionTokenizer(data=self._data[self._caret :])
        while True:
            token_info = tokenizer.get_token()
            if token_info.exact_type == tokenize.LBRACE:
                brace_depth += 1
            elif token_info.exact_type == tokenize.RBRACE:
                brace_depth -= 1
                if brace_depth < 0:
                    clean_expression: str = tokenize.untokenize(collected_tokens)
                    return tokenizer.position, clean_expression
            if token_info.exact_type not in self._IGNORED_TOKENS_TYPES:
                collected_tokens.append((token_info.type, token_info.string))
