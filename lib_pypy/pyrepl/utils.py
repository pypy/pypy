import builtins
import functools
import keyword
import re
import token as T
import tokenize
import unicodedata

from io import StringIO
from typing import Iterator, NamedTuple

ANSI_ESCAPE_SEQUENCE = re.compile(r"\x1b\[[ -@]*[A-~]")
IDENTIFIERS_AFTER = {"def", "class"}
KEYWORD_CONSTANTS = {"True", "False", "None"}
BUILTINS = {str(name) for name in dir(builtins) if not name.startswith("_")}


class Span(NamedTuple):
    start: int
    end: int

    @classmethod
    def from_token(cls, token, line_lengths):
        end_offset = -1
        if token.type == T.FSTRING_MIDDLE and token.string.endswith(("{", "}")):
            # A visible trailing brace comes from a doubled brace in the input.
            end_offset += 1
        return cls(
            line_lengths[token.start[0] - 1] + token.start[1],
            line_lengths[token.end[0] - 1] + token.end[1] + end_offset,
        )


class ColorSpan(NamedTuple):
    span: Span
    tag: str


def gen_colors(buffer: str) -> Iterator[ColorSpan]:
    sio = StringIO(buffer)
    line_lengths = [0] + [len(line) for line in sio.readlines()]
    for i in range(1, len(line_lengths)):
        line_lengths[i] += line_lengths[i - 1]
    sio.seek(0)
    last_emitted = None
    try:
        for color in gen_colors_from_token_stream(
            tokenize.generate_tokens(sio.readline), line_lengths
        ):
            yield color
            last_emitted = color
    except SyntaxError:
        return
    except tokenize.TokenError as error:
        yield from recover_unterminated_string(
            error, line_lengths, last_emitted, buffer
        )


def recover_unterminated_string(error, line_lengths, last_emitted, buffer):
    message, location = error.args
    if location is None:
        return
    line_no, column = location
    if message.startswith((
        "unterminated string literal",
        "unterminated f-string literal",
        "EOF in multi-line string",
        "unterminated triple-quoted f-string literal",
    )):
        start = line_lengths[line_no - 1] + column
        end = line_lengths[-1] - 1
        if last_emitted and start <= last_emitted.span.start:
            start = last_emitted.span.end + 1
        yield ColorSpan(Span(start, end), "STRING")


def gen_colors_from_token_stream(token_generator, line_lengths):
    is_definition_name = False
    bracket_level = 0
    string_tokens = {T.STRING, T.FSTRING_START, T.FSTRING_MIDDLE, T.FSTRING_END}
    for previous, token, following in prev_next_window(token_generator):
        if token.start == token.end:
            continue
        if token.type in string_tokens:
            tag = "STRING"
        elif token.type == T.COMMENT:
            tag = "COMMENT"
        elif token.type == T.NUMBER:
            tag = "NUMBER"
        elif token.type == T.OP:
            if token.string in "([{":
                bracket_level += 1
            elif token.string in ")]}":
                bracket_level -= 1
            tag = "OP"
        elif token.type == T.ERRORTOKEN and token.string in {'"', "'"}:
            # Python 3.12 represents an unfinished single-quoted string as an
            # ERRORTOKEN followed by ordinary tokens rather than TokenError.
            start = line_lengths[token.start[0] - 1] + token.start[1]
            end = line_lengths[token.start[0]] - 1
            yield ColorSpan(Span(start, end), "STRING")
            return
        elif token.type == T.NAME:
            if is_definition_name:
                is_definition_name = False
                tag = "DEFINITION"
            elif keyword.iskeyword(token.string):
                tag = ("KEYWORD_CONSTANT" if token.string in KEYWORD_CONSTANTS
                       else "KEYWORD")
                if token.string in IDENTIFIERS_AFTER:
                    is_definition_name = True
            elif (keyword.issoftkeyword(token.string) and bracket_level == 0
                  and is_soft_keyword_used(previous, token, following)):
                tag = "SOFT_KEYWORD"
            elif (token.string in BUILTINS
                  and not (previous and previous.exact_type == T.DOT)):
                tag = "BUILTIN"
            else:
                continue
        else:
            continue
        yield ColorSpan(Span.from_token(token, line_lengths), tag)


def is_soft_keyword_used(previous, token, following):
    if token.string == "_":
        return bool(previous and previous.string == "case"
                    and following and following.string == ":")
    at_statement_start = previous is None or previous.type in {
        T.NEWLINE, T.INDENT, T.DEDENT
    } or previous.string == ":"
    if not at_statement_start or following is None:
        return False
    if token.string == "type":
        return following.type == T.NAME and not keyword.iskeyword(following.string)
    if token.string not in {"match", "case"}:
        return False
    if following.type in {T.NUMBER, T.STRING, T.FSTRING_START, T.NAME}:
        return True
    allowed = "(*-[{~" if token.string == "case" else "(*-+[{~"
    return following.type == T.OP and following.string in allowed


def prev_next_window(iterable):
    iterator = iter(iterable)
    try:
        current = next(iterator)
    except StopIteration:
        return
    previous = None
    while True:
        try:
            following = next(iterator)
        except StopIteration:
            yield previous, current, None
            return
        except Exception:
            # Emit the last token obtained before propagating the tokenizer's
            # error on the next iteration.
            yield previous, current, None
            raise
        yield previous, current, following
        previous, current = current, following


@functools.cache
def str_width(c: str) -> int:
    if ord(c) < 128:
        return 1
    w = unicodedata.east_asian_width(c)
    if w in ('N', 'Na', 'H', 'A'):
        return 1
    return 2


def wlen(s: str) -> int:
    if len(s) == 1:
        return str_width(s)
    length = sum(str_width(i) for i in s)
    # remove lengths of any escape sequences
    sequence = ANSI_ESCAPE_SEQUENCE.findall(s)
    return length - sum(len(i) for i in sequence)
