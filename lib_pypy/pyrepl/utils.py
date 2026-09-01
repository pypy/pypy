import builtins
import functools
import keyword
import re
import token as T
import tokenize
import unicodedata
import _colorize  # type: ignore[import-not-found]

from io import StringIO
from typing import Iterator, NamedTuple

from .types import CharBuffer, CharWidths

ANSI_ESCAPE_SEQUENCE = re.compile(r"\x1b\[[ -@]*[A-~]")
ZERO_WIDTH_BRACKET = re.compile(r"\x01.*?\x02")
ZERO_WIDTH_TRANS = str.maketrans({"\x01": "", "\x02": ""})
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
    if unicodedata.combining(c):
        return 0
    category = unicodedata.category(c)
    if category == "Cf" and c != "\u00ad":
        return 0
    w = unicodedata.east_asian_width(c)
    if w in ('N', 'Na', 'H', 'A'):
        return 1
    return 2


def wlen(s: str) -> int:
    if len(s) == 1 and s != "\x1a":
        return str_width(s)
    length = sum(str_width(i) for i in s)
    # remove lengths of any escape sequences
    sequence = ANSI_ESCAPE_SEQUENCE.findall(s)
    return length - sum(len(i) for i in sequence) + s.count("\x1a")


def unbracket(s: str, including_content: bool = False) -> str:
    if including_content:
        return ZERO_WIDTH_BRACKET.sub("", s)
    return s.translate(ZERO_WIDTH_TRANS)


def disp_str(
    buffer: str, colors: list[ColorSpan] | None = None, start_index: int = 0
) -> tuple[CharBuffer, CharWidths]:
    """Convert source into one rendered cell and display width per character."""
    chars: CharBuffer = []
    char_widths: CharWidths = []
    if not buffer:
        return chars, char_widths

    while colors and colors[0].span.end < start_index:
        colors.pop(0)
    pre_color = ""
    if colors and colors[0].span.start < start_index:
        pre_color = _colorize.theme[colors[0].tag]

    for i, c in enumerate(buffer, start_index):
        if colors and colors[0].span.start == i:
            pre_color = _colorize.theme[colors[0].tag]
        if c == "\x1a":
            rendered = c
            char_widths.append(2)
        elif ord(c) < 128:
            rendered = c
            char_widths.append(1)
        elif unicodedata.category(c).startswith("C"):
            rendered = r"\u%04x" % ord(c)
            char_widths.append(len(rendered))
        else:
            rendered = c
            char_widths.append(str_width(c))

        post_color = ""
        if colors and colors[0].span.end == i:
            post_color = _colorize.theme["RESET"]
            colors.pop(0)
        chars.append(pre_color + rendered + post_color)
        pre_color = ""

    if colors and colors[0].span.start < i < colors[0].span.end:
        chars[-1] += _colorize.theme["RESET"]
    return chars, char_widths
