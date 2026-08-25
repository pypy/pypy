"""Regular expression tests specific to _sre.py and accumulated during TDD."""

import os
import py
from py.test import raises, skip
from pypy.interpreter.gateway import app2interp_temp


def init_app_test(cls, space):
    cls.w_s = space.appexec(
        [space.wrap(os.path.realpath(os.path.dirname(__file__)))],
        """(this_dir):
        import sys
        # Uh-oh, ugly hack
        sys.path.insert(0, this_dir)
        try:
            import support_test_app_sre
            return support_test_app_sre
        finally:
            sys.path.pop(0)
        """)


class AppTestSreMatch:
    spaceconfig = dict(usemodules=('array', ))

    def test_copy(self):
        import re
        # new in 3.7
        m = re.match("bla", "bla")
        assert m.__copy__() is m
        assert m.__deepcopy__("whatever") is m

    def test_match_attributes(self):
        import re
        c = re.compile("bla")
        m = c.match("blastring")
        assert "blastring" == m.string
        assert c == m.re
        assert 0 == m.pos
        assert 9 == m.endpos
        assert None == m.lastindex
        assert None == m.lastgroup
        assert ((0, 3),) == m.regs

    def test_match_attributes_with_groups(self):
        import re
        m = re.search("a(b)(?P<name>c)", "aabcd")
        assert 0 == m.pos
        assert 5 == m.endpos
        assert 2 == m.lastindex
        assert "name" == m.lastgroup
        assert ((1, 4), (2, 3), (3, 4)) == m.regs

    def test_regs_overlapping_groups(self):
        import re
        m = re.match("a((b)c)", "abc")
        assert ((0, 3), (1, 3), (1, 2)) == m.regs

    def test_start_end_span(self):
        import re
        m = re.search("a((b)c)", "aabcd")
        assert (1, 4) == (m.start(), m.end())
        assert (1, 4) == m.span()
        assert (2, 4) == (m.start(1), m.end(1))
        assert (2, 4) == m.span(1)
        assert (2, 3) == (m.start(2), m.end(2))
        assert (2, 3) == m.span(2)
        raises(IndexError, m.start, 3)
        raises(IndexError, m.end, 3)
        raises(IndexError, m.span, 3)
        raises(IndexError, m.start, -1)

    def test_groups(self):
        import re
        m = re.search("a((.).)", "aabcd")
        assert ("ab", "a") == m.groups()
        assert ("ab", "a") == m.groups(True)
        m = re.search("a((\d)|(\s))", "aa1b")
        assert ("1", "1", None) == m.groups()
        assert ("1", "1", True) == m.groups(True)
        m = re.search("a((\d)|(\s))", "a ")
        assert (" ", None, " ") == m.groups()
        m = re.match("(a)", "a")
        assert ("a",) == m.groups()

    def test_groupdict(self):
        import re
        m = re.search("a((.).)", "aabcd")
        assert {} == m.groupdict()
        m = re.search("a((?P<first>.).)", "aabcd")
        assert {"first": "a"} == m.groupdict()
        m = re.search("a((?P<first>\d)|(?P<second>\s))", "aa1b")
        assert {"first": "1", "second": None} == m.groupdict()
        assert {"first": "1", "second": True} == m.groupdict(True)

    def test_group(self):
        import re
        m = re.search("a((?P<first>\d)|(?P<second>\s))", "aa1b")
        assert "a1" == m.group()
        assert ("1", "1", None) == m.group(1, 2, 3)
        assert ("1", None) == m.group("first", "second")
        raises(IndexError, m.group, 1, 4)
        assert ("1", None) == m.group(1, "second")
        raises(IndexError, m.group, 'foobarbaz')
        raises(IndexError, m.group, 'first', 'foobarbaz')

    def test_group_takes_long(self):
        import re
        import sys
        if sys.version_info < (2, 7, 9):
            skip()
        assert re.match("(foo)", "foo").group(1) == "foo"
        exc = raises(IndexError, re.match("", "").group, sys.maxsize + 1)
        assert str(exc.value) == "no such group"

    def test_group_takes_index(self):
        import re
        class Index:
            def __init__(self, value):
                self.value = value
            def __index__(self):
                return self.value
        assert re.match("(foo)", "foo").group(Index(1)) == "foo"

    def test_getitem(self):
        import re
        assert re.match("(foo)bar", "foobar")[1] == "foo"

    def test_expand(self):
        import re
        m = re.search("a(..)(?P<name>..)", "ab1bc")
        assert "b1bcbc" == m.expand(r"\1\g<name>\2")

    def test_sub_bytes(self):
        import re
        assert b"bbbbb" == re.sub(b"a", b"b", b"ababa")
        assert (b"bbbbb", 3) == re.subn(b"a", b"b", b"ababa")
        assert b"dddd" == re.sub(b"[abc]", b"d", b"abcd")
        assert (b"dddd", 3) == re.subn(b"[abc]", b"d", b"abcd")
        assert b"rbd\nbr\n" == re.sub(b"a(.)", br"b\1\n", b"radar")
        assert (b"rbd\nbr\n", 2) == re.subn(b"a(.)", br"b\1\n", b"radar")
        assert (b"bbbba", 2) == re.subn(b"a", b"b", b"ababa", 2)

    def test_sub_unicode(self):
        import re
        assert isinstance(re.sub("a", "b", ""), str)
        # the input is returned unmodified if no substitution is performed,
        # which (if interpreted literally, as CPython does) gives the
        # following strangeish rules:
        assert isinstance(re.sub("a", "b", "diwoiioamoi"), str)
        raises(TypeError, re.sub, "a", "b", b"diwoiiobmoi")
        raises(TypeError, re.sub, 'x', b'y', b'x')

    def test_sub_callable(self):
        import re
        def call_me(match):
            ret = ""
            for char in match.group():
                ret += chr(ord(char) + 1)
            return ret
        assert ("bbbbb", 3) == re.subn("a", call_me, "ababa")

    def test_sub_callable_returns_none(self):
        import re
        def call_me(match):
            return None
        assert "acd" == re.sub("b", call_me, "abcd")

    def test_sub_subclass_of_str(self):
        import re
        class MyString(str):
            pass
        class MyBytes(bytes):
            pass
        s1 = MyString('zz')
        s2 = re.sub('aa', 'bb', s1)
        assert s2 == s1
        assert type(s2) is str       # and not MyString
        u1 = MyBytes(b'zz')
        u2 = re.sub(b'aa', b'bb', u1)
        assert u2 == u1
        assert type(u2) is bytes   # and not MyBytes

    def test_sub_bug(self):
        import re
        assert re.sub('=\w{2}', 'x', '=CA') == 'x'

    def test_sub_emptymatch(self):
        import re
        assert re.sub(r"b*", "*", "abc") == "*a**c*"

    def test_sub_shortcut_no_match(self):
        import re
        s = b"ccccccc"
        assert re.sub(b"a", b"b", s) is s
        s = u"ccccccc"
        assert re.sub(u"a", u"b", s) is s

    def test_sub_bytearray(self):
        import re
        assert re.sub(b'a', bytearray(b'A'), b'axa') == b'AxA'
        # this fails on CPython 3.5:
        assert re.sub(b'a', bytearray(b'\\n'), b'axa') == b'\nx\n'

    def test_match_array(self):
        import re, array
        a = array.array('b', b'hello')
        m = re.match(b'hel+', a)
        assert m.end() == 4

    def test_match_typeerror(self):
        import re
        raises(TypeError, re.match, 'hel+', list('hello'))

    def test_match_repr(self):
        import re
        m = re.search("ab+c", "xabbbcd")
        assert repr(m) == "<re.Match object; span=(1, 6), match='abbbc'>"

    def test_unicode_iscased(self):
        import _sre
        assert _sre.unicode_iscased(64261)
        assert not _sre.unicode_iscased(32)

    def test_group_bugs(self):
        import re
        r = re.compile(r"""
            \&(?:
              (?P<escaped>\&) |
              (?P<named>[_a-z][_a-z0-9]*)      |
              {(?P<braced>[_a-z][_a-z0-9]*)}   |
              (?P<invalid>)
            )
        """, re.IGNORECASE | re.VERBOSE)
        matches = list(r.finditer('this &gift is for &{who} &&'))
        assert len(matches) == 3
        assert matches[0].groupdict() == {'escaped': None,
                                          'named': 'gift',
                                          'braced': None,
                                          'invalid': None}
        assert matches[1].groupdict() == {'escaped': None,
                                          'named': None,
                                          'braced': 'who',
                                          'invalid': None}
        assert matches[2].groupdict() == {'escaped': '&',
                                          'named': None,
                                          'braced': None,
                                          'invalid': None}
        matches = list(r.finditer('&who likes &{what)'))   # note the ')'
        assert len(matches) == 2
        assert matches[0].groupdict() == {'escaped': None,
                                          'named': 'who',
                                          'braced': None,
                                          'invalid': None}
        assert matches[1].groupdict() == {'escaped': None,
                                          'named': None,
                                          'braced': None,
                                          'invalid': ''}

    def test_sub_typecheck(self):
        import re
        KEYCRE = re.compile(r"%\(([^)]*)\)s|.")
        raises(TypeError, KEYCRE.sub, "hello", {"%(": 1})

    def test_sub_matches_stay_valid(self):
        import re
        matches = []
        def callback(match):
            matches.append(match)
            return "x"
        result = re.compile(r"[ab]").sub(callback, "acb")
        assert result == "xcx"
        assert len(matches) == 2
        assert matches[0].group() == "a"
        assert matches[1].group() == "b"


class AppTestGetlower:
    spaceconfig = dict(usemodules=('_locale',))

    def setup_class(cls):
        # This imports support_test_sre as the global "s"
        init_app_test(cls, cls.space)

    def setup_method(self, method):
        import locale
        locale.setlocale(locale.LC_ALL, (None, None))

    def teardown_method(self, method):
        import locale
        locale.setlocale(locale.LC_ALL, (None, None))

    def test_getlower_no_flags(self):
        s = self.s
        UPPER_AE = "\xc4"
        s.assert_lower_equal([("a", "a"), ("A", "a"), (UPPER_AE, UPPER_AE),
            ("\u00c4", "\u00c4"), ("\u4444", "\u4444")], 0)

    def test_getlower_unicode(self):
        s = self.s
        import sre_constants
        UPPER_AE = "\xc4"
        LOWER_AE = "\xe4"
        UPPER_PI = "\u03a0"
        LOWER_PI = "\u03c0"
        s.assert_lower_equal([("a", "a"), ("A", "a"), (UPPER_AE, LOWER_AE),
            ("\u00c4", "\u00e4"), (UPPER_PI, LOWER_PI),
            ("\u4444", "\u4444")], sre_constants.SRE_FLAG_UNICODE)
