import re
from pypy.rlib.rsre import rsre_core
from pypy.rlib.rsre.rpy import get_code


def get_code_and_re(regexp):
    return get_code(regexp), re.compile(regexp)

def test_get_code_repetition():
    c1 = get_code(r"a+")
    c2 = get_code(r"a+")
    assert c1 == c2


class TestMatch:

    def test_or(self):
        r = get_code(r"a|bc|def")
        assert rsre_core.match(r, "a")
        assert rsre_core.match(r, "bc")
        assert rsre_core.match(r, "def")
        assert not rsre_core.match(r, "ghij")

    def test_any(self):
        r = get_code(r"ab.cd")
        assert rsre_core.match(r, "abXcdef")
        assert not rsre_core.match(r, "ab\ncdef")
        assert not rsre_core.match(r, "abXcDef")

    def test_any_repetition(self):
        r = get_code(r"ab.*cd")
        assert rsre_core.match(r, "abXXXXcdef")
        assert rsre_core.match(r, "abcdef")
        assert not rsre_core.match(r, "abX\nXcdef")
        assert not rsre_core.match(r, "abXXXXcDef")

    def test_any_all(self):
        r = get_code(r"(?s)ab.cd")
        assert rsre_core.match(r, "abXcdef")
        assert rsre_core.match(r, "ab\ncdef")
        assert not rsre_core.match(r, "ab\ncDef")

    def test_any_all_repetition(self):
        r = get_code(r"(?s)ab.*cd")
        assert rsre_core.match(r, "abXXXXcdef")
        assert rsre_core.match(r, "abcdef")
        assert rsre_core.match(r, "abX\nXcdef")
        assert not rsre_core.match(r, "abX\nXcDef")

    def test_assert(self):
        r = get_code(r"abc(?=def)(.)")
        res = rsre_core.match(r, "abcdefghi")
        assert res is not None and res.get_mark(1) == 4
        assert not rsre_core.match(r, "abcdeFghi")

    def test_assert_not(self):
        r = get_code(r"abc(?!def)(.)")
        res = rsre_core.match(r, "abcdeFghi")
        assert res is not None and res.get_mark(1) == 4
        assert not rsre_core.match(r, "abcdefghi")

    def test_lookbehind(self):
        r = get_code(r"([a-z]*)(?<=de)")
        assert rsre_core.match(r, "ade")
        res = rsre_core.match(r, "adefg")
        assert res is not None and res.get_mark(1) == 3
        assert not rsre_core.match(r, "abc")
        assert not rsre_core.match(r, "X")
        assert not rsre_core.match(r, "eX")

    def test_negative_lookbehind(self):
        def found(s):
            res = rsre_core.match(r, s)
            assert res is not None
            return res.get_mark(1)
        r = get_code(r"([a-z]*)(?<!dd)")
        assert found("ade") == 3
        assert found("adefg") == 5
        assert found("abcdd") == 4
        assert found("abddd") == 3
        assert found("adddd") == 2
        assert found("ddddd") == 1
        assert found("abXde") == 2

    def test_at(self):
        r = get_code(r"abc$")
        assert rsre_core.match(r, "abc")
        assert not rsre_core.match(r, "abcd")
        assert not rsre_core.match(r, "ab")

    def test_repeated_set(self):
        r = get_code(r"[a0x]+f")
        assert rsre_core.match(r, "a0af")
        assert not rsre_core.match(r, "a0yaf")

    def test_category(self):
        r = get_code(r"[\sx]")
        assert rsre_core.match(r, "x")
        assert rsre_core.match(r, " ")
        assert not rsre_core.match(r, "n")

    def test_groupref(self):
        r = get_code(r"(xx+)\1+$")     # match non-prime numbers of x
        assert not rsre_core.match(r, "xx")
        assert not rsre_core.match(r, "xxx")
        assert     rsre_core.match(r, "xxxx")
        assert not rsre_core.match(r, "xxxxx")
        assert     rsre_core.match(r, "xxxxxx")
        assert not rsre_core.match(r, "xxxxxxx")
        assert     rsre_core.match(r, "xxxxxxxx")
        assert     rsre_core.match(r, "xxxxxxxxx")

    def test_groupref_ignore(self):
        r = get_code(r"(?i)(xx+)\1+$")     # match non-prime numbers of x
        assert not rsre_core.match(r, "xX")
        assert not rsre_core.match(r, "xxX")
        assert     rsre_core.match(r, "Xxxx")
        assert not rsre_core.match(r, "xxxXx")
        assert     rsre_core.match(r, "xXxxxx")
        assert not rsre_core.match(r, "xxxXxxx")
        assert     rsre_core.match(r, "xxxxxxXx")
        assert     rsre_core.match(r, "xxxXxxxxx")

    def test_groupref_exists(self):
        r = get_code(r"((a)|(b))c(?(2)d)$")
        assert not rsre_core.match(r, "ac")
        assert     rsre_core.match(r, "acd")
        assert     rsre_core.match(r, "bc")
        assert not rsre_core.match(r, "bcd")
        #
        r = get_code(r"((a)|(b))c(?(2)d|e)$")
        assert not rsre_core.match(r, "ac")
        assert     rsre_core.match(r, "acd")
        assert not rsre_core.match(r, "ace")
        assert not rsre_core.match(r, "bc")
        assert not rsre_core.match(r, "bcd")
        assert     rsre_core.match(r, "bce")

    def test_in_ignore(self):
        r = get_code(r"(?i)[a-f]")
        assert rsre_core.match(r, "b")
        assert rsre_core.match(r, "C")
        assert not rsre_core.match(r, "g")
        r = get_code(r"(?i)[a-f]+$")
        assert rsre_core.match(r, "bCdEf")
        assert not rsre_core.match(r, "g")
        assert not rsre_core.match(r, "aaagaaa")

    def test_not_literal(self):
        r = get_code(r"[^a]")
        assert rsre_core.match(r, "A")
        assert not rsre_core.match(r, "a")
        r = get_code(r"[^a]+$")
        assert rsre_core.match(r, "Bx123")
        assert not rsre_core.match(r, "--a--")

    def test_not_literal_ignore(self):
        r = get_code(r"(?i)[^a]")
        assert rsre_core.match(r, "G")
        assert not rsre_core.match(r, "a")
        assert not rsre_core.match(r, "A")
        r = get_code(r"(?i)[^a]+$")
        assert rsre_core.match(r, "Gx123")
        assert not rsre_core.match(r, "--A--")

    def test_repeated_single_character_pattern(self):
        r = get_code(r"foo(?:(?<=foo)x)+$")
        assert rsre_core.match(r, "foox")

    def test_flatten_marks(self):
        r = get_code(r"a(b)c((d)(e))+$")
        res = rsre_core.match(r, "abcdedede")
        assert res.flatten_marks() == [0, 9, 1, 2, 7, 9, 7, 8, 8, 9]
        assert res.flatten_marks() == [0, 9, 1, 2, 7, 9, 7, 8, 8, 9]

    def test_bug1(self):
        # REPEAT_ONE inside REPEAT
        r = get_code(r"(?:.+)?B")
        assert rsre_core.match(r, "AB") is not None
        r = get_code(r"(?:AA+?)+B")
        assert rsre_core.match(r, "AAAB") is not None
        r = get_code(r"(?:AA+)+?B")
        assert rsre_core.match(r, "AAAB") is not None
        r = get_code(r"(?:AA+?)+?B")
        assert rsre_core.match(r, "AAAB") is not None
        # REPEAT inside REPEAT
        r = get_code(r"(?:(?:xy)+)?B")
        assert rsre_core.match(r, "xyB") is not None
        r = get_code(r"(?:xy(?:xy)+?)+B")
        assert rsre_core.match(r, "xyxyxyB") is not None
        r = get_code(r"(?:xy(?:xy)+)+?B")
        assert rsre_core.match(r, "xyxyxyB") is not None
        r = get_code(r"(?:xy(?:xy)+?)+?B")
        assert rsre_core.match(r, "xyxyxyB") is not None

    def test_assert_group(self):
        r = get_code(r"abc(?=(..)f)(.)")
        res = rsre_core.match(r, "abcdefghi")
        assert res is not None
        assert res.span(2) == (3, 4)
        assert res.span(1) == (3, 5)

    def test_assert_not_group(self):
        r = get_code(r"abc(?!(de)f)(.)")
        res = rsre_core.match(r, "abcdeFghi")
        assert res is not None
        assert res.span(2) == (3, 4)
        # this I definitely classify as Horrendously Implementation Dependent.
        # CPython answers (3, 5).
        assert res.span(1) == (-1, -1)

    def test_match_start(self):
        r = get_code(r"^ab")
        assert     rsre_core.match(r, "abc")
        assert not rsre_core.match(r, "xxxabc", start=3)
        assert not rsre_core.match(r, "xx\nabc", start=3)
        #
        r = get_code(r"(?m)^ab")
        assert     rsre_core.match(r, "abc")
        assert not rsre_core.match(r, "xxxabc", start=3)
        assert     rsre_core.match(r, "xx\nabc", start=3)

    def test_match_end(self):
        r = get_code("ab")
        assert     rsre_core.match(r, "abc")
        assert     rsre_core.match(r, "abc", end=333)
        assert     rsre_core.match(r, "abc", end=3)
        assert     rsre_core.match(r, "abc", end=2)
        assert not rsre_core.match(r, "abc", end=1)
        assert not rsre_core.match(r, "abc", end=0)
        assert not rsre_core.match(r, "abc", end=-1)

    def test_match_bug1(self):
        r = get_code(r'(x??)?$')
        assert rsre_core.match(r, "x")

    def test_match_bug2(self):
        r = get_code(r'(x??)??$')
        assert rsre_core.match(r, "x")

    def test_match_bug3(self):
        r = get_code(r'([ax]*?x*)?$')
        assert rsre_core.match(r, "aaxaa")
