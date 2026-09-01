from unittest import TestCase

from pyrepl.utils import gen_colors, prev_next_window


class TestUtils(TestCase):
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
