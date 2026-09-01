from unittest import TestCase

from pyrepl.utils import gen_colors, prev_next_window, str_width, wlen


class TestUtils(TestCase):
    def test_str_width(self):
        for character in [
            "a", "1", "_", "!", "\x1a", "\u263a", "\uffb9",
            "é", "\N{LATIN SMALL LETTER E WITH CEDILLA}", "\u00ad",
        ]:
            with self.subTest(character=character):
                self.assertEqual(str_width(character), 1)

        for character in [
            "\N{COMBINING ACUTE ACCENT}",
            "\N{ZERO WIDTH JOINER}",
        ]:
            with self.subTest(character=character):
                self.assertEqual(str_width(character), 0)

        for character in [chr(99989), chr(99999)]:
            self.assertEqual(str_width(character), 2)

    def test_wlen(self):
        for character in ["a", "b", "1", "!", "_"]:
            self.assertEqual(wlen(character), 1)
        self.assertEqual(wlen("\x1a"), 2)
        self.assertEqual(wlen(chr(3800)), 1)
        self.assertEqual(wlen(chr(4352)), 2)
        self.assertEqual(wlen("hello"), 5)
        self.assertEqual(wlen("hello\x1a"), 7)
        self.assertEqual(wlen("e\N{COMBINING ACUTE ACCENT}"), 1)
        self.assertEqual(wlen("a\N{ZERO WIDTH JOINER}b"), 2)

    def test_prev_next_window(self):
        expected = [
            (None, 1, 2),
            (1, 2, 3),
            (2, 3, 4),
            (3, 4, None),
        ]
        self.assertEqual(list(prev_next_window(iter([1, 2, 3, 4]))), expected)
        self.assertEqual(list(prev_next_window(iter([1]))), [(None, 1, None)])

        def raising_generator():
            yield from [1, 2, 3, 4]
            raise ZeroDivisionError

        window = prev_next_window(raising_generator())
        for item in expected:
            self.assertEqual(next(window), item)
        with self.assertRaises(ZeroDivisionError):
            next(window)

    def test_gen_colors_keyword_highlighting(self):
        cases = [
            ("a.set", [(".", "OP")]),
            ("obj.list", [(".", "OP")]),
            ("obj.match", [(".", "OP")]),
            ("b. \\\n format", [(".", "OP")]),
            ("set", [("set", "BUILTIN")]),
            ("list", [("list", "BUILTIN")]),
            ("    \n dict", [("dict", "BUILTIN")]),
            ("match +1", [
                ("match", "SOFT_KEYWORD"),
                ("+", "OP"),
                ("1", "NUMBER"),
            ]),
            ("match -1", [
                ("match", "SOFT_KEYWORD"),
                ("-", "OP"),
                ("1", "NUMBER"),
            ]),
        ]
        for code, expected in cases:
            with self.subTest(code=code):
                actual = [
                    (code[color.span.start:color.span.end + 1], color.tag)
                    for color in gen_colors(code)
                ]
                self.assertEqual(actual, expected)
