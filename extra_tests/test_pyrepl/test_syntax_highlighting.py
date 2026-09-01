from pyrepl.reader import Reader, disp_str
from pyrepl.utils import gen_colors


def highlighted_parts(source):
    return [(source[c.span.start:c.span.end + 1], c.tag)
            for c in gen_colors(source)]


def test_token_colors():
    source = "def answer(value: int = 42): # comment\n    return str(value)"
    assert highlighted_parts(source) == [
        ("def", "KEYWORD"), ("answer", "DEFINITION"), ("(", "OP"),
        (":", "OP"), ("int", "BUILTIN"), ("=", "OP"),
        ("42", "NUMBER"), (")", "OP"), (":", "OP"),
        ("# comment", "COMMENT"), ("return", "KEYWORD"),
        ("str", "BUILTIN"), ("(", "OP"), (")", "OP"),
    ]


def test_incomplete_strings_are_colored():
    for source, expected in [
        ('value = "still typing', '"still typing'),
        ("value = '''two\nlines", "'''two\nlines"),
    ]:
        assert highlighted_parts(source)[-1] == (expected, "STRING")


def test_fstring_expressions_are_colored_as_python():
    parts = highlighted_parts('f"value={1 + len(items)}"')
    assert ("value=", "STRING") in parts
    assert ("1", "NUMBER") in parts
    assert ("len", "BUILTIN") in parts
    assert ("+", "OP") in parts


def test_builtin_attribute_is_not_colored():
    assert highlighted_parts("obj.list") == [(".", "OP")]


def test_renderer_keeps_ansi_out_of_widths():
    source = "def f"
    chars, widths = disp_str(source, list(gen_colors(source)))
    assert len(chars) == len(source)
    assert widths == [1] * len(source)
    assert "\x1b[" in "".join(chars)


class FakeConsole:
    width = 80
    height = 24


def test_reader_screen_contains_highlighting_but_cursor_uses_source_positions():
    reader = Reader(FakeConsole())
    reader.can_colorize = True
    reader.buffer[:] = "def f():\n    return 42"
    reader.pos = len(reader.buffer)
    screen = reader.calc_screen()
    assert "\x1b[" in "".join(screen)
    assert reader.cxy == (17, 1)  # 13 source columns plus the four-column prompt
    assert reader.screeninfo[1][1] == [1] * 13
