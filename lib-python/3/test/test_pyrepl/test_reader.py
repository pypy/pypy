import itertools
import functools
import rlcompleter
from textwrap import dedent
from unittest import TestCase
from unittest.mock import MagicMock, patch

from .support import (ScreenEqualMixin, handle_all_events,
                      handle_events_narrow_console, code_to_events,
                      prepare_console, prepare_reader)
from test.support import cpython_only, force_colorized_test_class, import_helper
from pyrepl.console import Event
from pyrepl.reader import Reader
from _colorize import theme


_overrides = {"RESET": "z", "SOFT_KEYWORD": "K"}
_syntax_colors = {
    _overrides.get(name, name[0].lower()): value
    for name, value in theme.items()
}


class TestReader(TestCase):
    def assert_screen_equals(self, reader, expected):
        actual = reader.screen
        expected = expected.split("\n")
        self.assertListEqual(actual, expected)

    def test_calc_screen_wrap_simple(self):
        events = code_to_events(10 * "a")
        reader, _ = handle_events_narrow_console(events)
        self.assert_screen_equals(reader, f"{9*'a'}\\\na")

    def test_calc_screen_wrap_wide_characters(self):
        events = code_to_events(8 * "a" + "樂")
        reader, _ = handle_events_narrow_console(events)
        self.assert_screen_equals(reader, f"{8*'a'}\\\n樂")

    def test_calc_screen_wrap_three_lines(self):
        events = code_to_events(20 * "a")
        reader, _ = handle_events_narrow_console(events)
        self.assert_screen_equals(reader, f"{9*'a'}\\\n{9*'a'}\\\naa")

    def test_calc_screen_prompt_handling(self):
        def prepare_reader_keep_prompts(*args, **kwargs):
            reader = prepare_reader(*args, **kwargs)
            del reader.get_prompt
            reader.ps1 = ">>> "
            reader.ps2 = ">>> "
            reader.ps3 = "... "
            reader.ps4 = ""
            reader.can_colorize = False
            reader.paste_mode = False
            return reader

        events = code_to_events("if some_condition:\nsome_function()")
        reader, _ = handle_events_narrow_console(
            events,
            prepare_reader=prepare_reader_keep_prompts,
        )
        # fmt: off
        self.assert_screen_equals(
            reader,
            (
            ">>> if so\\\n"
            "me_condit\\\n"
            "ion:\n"
            "...     s\\\n"
            "ome_funct\\\n"
            "ion()"
            )
        )
        # fmt: on

    def test_calc_screen_wrap_three_lines_mixed_character(self):
        # fmt: off
        code = (
            "def f():\n"
           f"  {8*'a'}\n"
           f"  {5*'樂'}"
        )
        # fmt: on

        events = code_to_events(code)
        reader, _ = handle_events_narrow_console(events)

        # fmt: off
        self.assert_screen_equals(reader, (
            "def f():\n"
           f"  {7*'a'}\\\n"
            "a\n"
           f"  {3*'樂'}\\\n"
            "樂樂"
        ))
        # fmt: on

    def test_calc_screen_backspace(self):
        events = itertools.chain(
            code_to_events("aaa"),
            [
                Event(evt="key", data="backspace", raw=bytearray(b"\x7f")),
            ],
        )
        reader, _ = handle_all_events(events)
        self.assert_screen_equals(reader, "aa")

    def test_calc_screen_wrap_removes_after_backspace(self):
        events = itertools.chain(
            code_to_events(10 * "a"),
            [
                Event(evt="key", data="backspace", raw=bytearray(b"\x7f")),
            ],
        )
        reader, _ = handle_events_narrow_console(events)
        self.assert_screen_equals(reader, 9 * "a")

    def test_calc_screen_backspace_in_second_line_after_wrap(self):
        events = itertools.chain(
            code_to_events(11 * "a"),
            [
                Event(evt="key", data="backspace", raw=bytearray(b"\x7f")),
            ],
        )
        reader, _ = handle_events_narrow_console(events)
        self.assert_screen_equals(reader, f"{9*'a'}\\\na")

    def test_setpos_for_xy_simple(self):
        events = code_to_events("11+11")
        reader, _ = handle_all_events(events)
        reader.setpos_from_xy(0, 0)
        self.assertEqual(reader.pos, 0)

    def test_control_characters(self):
        code = 'flag = "🏳️‍🌈"'
        events = code_to_events(code)
        reader, _ = handle_all_events(events)
        self.assert_screen_equals(reader, 'flag = "🏳️\\u200d🌈"')

    def test_setpos_from_xy_multiple_lines(self):
        # fmt: off
        code = (
            "def foo():\n"
            "  return 1"
        )
        # fmt: on

        events = code_to_events(code)
        reader, _ = handle_all_events(events)
        reader.setpos_from_xy(2, 1)
        self.assertEqual(reader.pos, 13)

    def test_setpos_from_xy_after_wrap(self):
        # fmt: off
        code = (
            "def foo():\n"
            "  hello"
        )
        # fmt: on

        events = code_to_events(code)
        reader, _ = handle_events_narrow_console(events)
        reader.setpos_from_xy(2, 2)
        self.assertEqual(reader.pos, 13)

    def test_setpos_fromxy_in_wrapped_line(self):
        # fmt: off
        code = (
            "def foo():\n"
            "  hello"
        )
        # fmt: on

        events = code_to_events(code)
        reader, _ = handle_events_narrow_console(events)
        reader.setpos_from_xy(0, 1)
        self.assertEqual(reader.pos, 9)

    def test_up_arrow_after_ctrl_r(self):
        events = iter(
            [
                Event(evt="key", data="\x12", raw=bytearray(b"\x12")),
                Event(evt="key", data="up", raw=bytearray(b"\x1bOA")),
            ]
        )

        reader, _ = handle_all_events(events)
        self.assert_screen_equals(reader, "")

    def test_newline_within_block_trailing_whitespace(self):
        # fmt: off
        code = (
            "def foo():\n"
                 "a = 1\n"
        )
        # fmt: on

        events = itertools.chain(
            code_to_events(code),
            [
                # go to the end of the first line
                Event(evt="key", data="up", raw=bytearray(b"\x1bOA")),
                Event(evt="key", data="up", raw=bytearray(b"\x1bOA")),
                Event(evt="key", data="\x05", raw=bytearray(b"\x1bO5")),
                # new lines in-block shouldn't terminate the block
                Event(evt="key", data="\n", raw=bytearray(b"\n")),
                Event(evt="key", data="\n", raw=bytearray(b"\n")),
                # end of line 2
                Event(evt="key", data="down", raw=bytearray(b"\x1bOB")),
                Event(evt="key", data="\x05", raw=bytearray(b"\x1bO5")),
                # a double new line in-block should terminate the block
                # even if its followed by whitespace
                Event(evt="key", data="\n", raw=bytearray(b"\n")),
                Event(evt="key", data="\n", raw=bytearray(b"\n")),
            ],
        )

        no_paste_reader = functools.partial(prepare_reader, paste_mode=False)
        reader, _ = handle_all_events(events, prepare_reader=no_paste_reader)

        expected = (
            "def foo():\n"
            "    \n"
            "    \n"
            "    a = 1\n"
            "    \n"
            "    "    # HistoricalReader will trim trailing whitespace
        )
        self.assert_screen_equals(reader, expected)
        self.assertTrue(reader.finished)

    def test_input_hook_is_called_if_set(self):
        input_hook = MagicMock()
        def _prepare_console(events):
            console = MagicMock()
            console.get_event.side_effect = events
            console.height = 100
            console.width = 80
            console.getheightwidth = MagicMock(
                side_effect=lambda: (console.height, console.width)
            )
            console.input_hook = input_hook
            return console

        events = code_to_events("a")
        reader, _ = handle_all_events(events, prepare_console=_prepare_console)

        self.assertEqual(len(input_hook.mock_calls), 4)

    def test_keyboard_interrupt_clears_screen(self):
        namespace = {"itertools": itertools}
        code = "import itertools\nitertools."
        events = itertools.chain(code_to_events(code), [
            Event(evt='key', data='\t', raw=bytearray(b'\t')),  # Two tabs for completion
            Event(evt='key', data='\t', raw=bytearray(b'\t')),
            Event(evt='key', data='\x03', raw=bytearray(b'\x03')),  # Ctrl-C
        ])

        completing_reader = functools.partial(
            prepare_reader,
            readline_completer=rlcompleter.Completer(namespace).complete
        )
        reader, _ = handle_all_events(events, prepare_reader=completing_reader)
        self.assertEqual(reader.calc_screen(), code.split("\n"))

    def test_prompt_length(self):
        # Handles simple ASCII prompt
        ps1 = ">>> "
        prompt, l = Reader.process_prompt(ps1)
        self.assertEqual(prompt, ps1)
        self.assertEqual(l, 4)

        # Handles ANSI escape sequences
        ps1 = "\033[0;32m>>> \033[0m"
        prompt, l = Reader.process_prompt(ps1)
        self.assertEqual(prompt, "\033[0;32m>>> \033[0m")
        self.assertEqual(l, 4)

        # Handles ANSI escape sequences bracketed in \001 .. \002
        ps1 = "\001\033[0;32m\002>>> \001\033[0m\002"
        prompt, l = Reader.process_prompt(ps1)
        self.assertEqual(prompt, "\033[0;32m>>> \033[0m")
        self.assertEqual(l, 4)

        # Handles wide characters in prompt
        ps1 = "樂>> "
        prompt, l = Reader.process_prompt(ps1)
        self.assertEqual(prompt, ps1)
        self.assertEqual(l, 5)

        # Handles wide characters AND ANSI sequences together
        ps1 = "\001\033[0;32m\002樂>\001\033[0m\002> "
        prompt, l = Reader.process_prompt(ps1)
        self.assertEqual(prompt, "\033[0;32m樂>\033[0m> ")
        self.assertEqual(l, 5)

    def test_completions_updated_on_key_press(self):
        namespace = {"itertools": itertools}
        code = "itertools."
        events = itertools.chain(code_to_events(code), [
            Event(evt='key', data='\t', raw=bytearray(b'\t')),  # Two tabs for completion
            Event(evt='key', data='\t', raw=bytearray(b'\t')),
        ], code_to_events("a"))

        completing_reader = functools.partial(
            prepare_reader,
            readline_completer=rlcompleter.Completer(namespace).complete
        )
        reader, _ = handle_all_events(events, prepare_reader=completing_reader)

        actual = reader.screen
        self.assertEqual(len(actual), 2)
        self.assertEqual(actual[0].rstrip(), "itertools.accumulate(")
        self.assertEqual(actual[1], f"{code}a")

    def test_key_press_on_tab_press_once(self):
        namespace = {"itertools": itertools}
        code = "itertools."
        events = itertools.chain(code_to_events(code), [
            Event(evt='key', data='\t', raw=bytearray(b'\t')),
        ], code_to_events("a"))

        completing_reader = functools.partial(
            prepare_reader,
            readline_completer=rlcompleter.Completer(namespace).complete
        )
        reader, _ = handle_all_events(events, prepare_reader=completing_reader)

        self.assert_screen_equals(reader, f"{code}a")

    def test_pos2xy_with_no_columns(self):
        console = prepare_console([])
        reader = prepare_reader(console)
        # Simulate a resize to 0 columns.
        reader.screeninfo = []
        self.assertEqual(reader.pos2xy(), (0, 0))

    def test_setpos_from_xy_for_non_printing_char(self):
        code = "# non \u200c printing character"
        events = code_to_events(code)

        reader, _ = handle_all_events(events)
        reader.setpos_from_xy(8, 0)
        self.assertEqual(reader.pos, 7)


@force_colorized_test_class
class TestReaderInColor(ScreenEqualMixin, TestCase):
    def test_syntax_highlighting_basic(self):
        code = dedent("""\
            import re, sys
            def funct(case: str = sys.platform) -> None:
                match case:
                    case "web": print("online")
                    case _: print('other', len(case))
            type Alias = list[int]
            """)
        expected = dedent("""\
            {k}import{z} re{o},{z} sys
            {k}def{z} {d}funct{z}{o}({z}case{o}:{z} {b}str{z} {o}={z} sys{o}.{z}platform{o}){z} {o}->{z} {k}None{z}{o}:{z}
                {K}match{z} case{o}:{z}
                    {K}case{z} {s}"web"{z}{o}:{z} {b}print{z}{o}({z}{s}"online"{z}{o}){z}
                    {K}case{z} {K}_{z}{o}:{z} {b}print{z}{o}({z}{s}'other'{z}{o},{z} {b}len{z}{o}({z}case{o}){z}{o}){z}
            {K}type{z} Alias {o}={z} {b}list{z}{o}[{z}{b}int{z}{o}]{z}
            """).format(**_syntax_colors)
        reader, _ = handle_all_events(code_to_events(code))
        self.assert_screen_equal(reader, code, clean=True)
        self.assert_screen_equal(reader, expected)

    def test_syntax_highlighting_incomplete_string_first_line(self):
        code = 'def unfinished(arg: str = "still typing'
        expected = (
            '{k}def{z} {d}unfinished{z}{o}({z}arg{o}:{z} {b}str{z} '
            '{o}={z} {s}"still typing{z}'
        ).format(**_syntax_colors)
        reader, _ = handle_all_events(code_to_events(code))
        self.assert_screen_equal(reader, expected)

    def test_syntax_highlighting_incomplete_string_another_line(self):
        code = 'def unfinished(\n    arg: str = "still typing'
        expected = (
            '{k}def{z} {d}unfinished{z}{o}({z}\n'
            '    arg{o}:{z} {b}str{z} {o}={z} {s}"still typing{z}'
        ).format(**_syntax_colors)
        reader, _ = handle_all_events(code_to_events(code))
        self.assert_screen_equal(reader, expected)

    def test_syntax_highlighting_incomplete_multiline_string(self):
        code = "def f():\n    '''Still writing\n    the docstring"
        expected = (
            "{k}def{z} {d}f{z}{o}({z}{o}){z}{o}:{z}\n"
            "    {s}'''Still writing{z}\n"
            "{s}    the docstring{z}"
        ).format(**_syntax_colors)
        reader, _ = handle_all_events(code_to_events(code))
        self.assert_screen_equal(reader, expected)

    @cpython_only
    def test_syntax_highlighting_incomplete_fstring(self):
        code = dedent("""\
            def unfinished_function():
                var = f"Single-quote but {
                1
                +
                1
                } multi-line!
            """)
        expected = dedent("""\
            {k}def{z} {d}unfinished_function{z}{o}({z}{o}){z}{o}:{z}
                var {o}={z} {s}f"{z}{s}Single-quote but {z}{o}{OB}{z}
                {n}1{z}
                {o}+{z}
                {n}1{z}
                {o}{CB}{z}{s} multi-line!{z}
            """).format(OB="{", CB="}", **_syntax_colors)
        reader, _ = handle_all_events(code_to_events(code))
        self.assert_screen_equal(reader, expected)

    def test_syntax_highlighting_indentation_error(self):
        code = "def f():\n    value = 1\n   oops"
        expected = (
            "{k}def{z} {d}f{z}{o}({z}{o}){z}{o}:{z}\n"
            "    value {o}={z} {n}1{z}\n"
            "   oops"
        ).format(**_syntax_colors)
        reader, _ = handle_all_events(code_to_events(code))
        self.assert_screen_equal(reader, expected)

    def test_syntax_highlighting_literal_braces_in_fstrings(self):
        code = (
            'f"{{"\n'
            'f"}}"\n'
            'f"a{{b"\n'
            'f"a}}b"\n'
            'f"a{{b}}c"\n'
            'f"{{{0}}}"\n'
            'f"{ {0} }"'
        )
        expected = (
            '{s}f"{z}{s}<<{z}{s}"{z}\n'
            '{s}f"{z}{s}>>{z}{s}"{z}\n'
            '{s}f"{z}{s}a<<{z}{s}b{z}{s}"{z}\n'
            '{s}f"{z}{s}a>>{z}{s}b{z}{s}"{z}\n'
            '{s}f"{z}{s}a<<{z}{s}b>>{z}{s}c{z}{s}"{z}\n'
            '{s}f"{z}{s}<<{z}{o}<{z}{n}0{z}{o}>{z}{s}>>{z}{s}"{z}\n'
            '{s}f"{z}{o}<{z} {o}<{z}{n}0{z}{o}>{z} {o}>{z}{s}"{z}'
        ).format(**_syntax_colors).replace("<", "{").replace(">", "}")
        reader, _ = handle_all_events(code_to_events(code))
        self.assert_screen_equal(reader, expected)
