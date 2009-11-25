"""Regular expression tests specific to _sre.py and accumulated during TDD."""
import autopath
from py.test import raises, skip
from pypy.interpreter.gateway import app2interp_temp
from pypy.conftest import gettestobjspace, option
from py.impl.test.outcome import Skipped

def init_globals_hack(space):
    space.appexec([space.wrap(autopath.this_dir)], """(this_dir):
    import __builtin__ as b
    import sys, os.path
    # Uh-oh, ugly hack
    sys.path.insert(0, this_dir)
    import support_test_app_sre
    b.s = support_test_app_sre
    sys.path.pop(0)
    """)

class AppTestSrePy:

    def test_magic(self):
        import _sre, sre_constants
        assert sre_constants.MAGIC == _sre.MAGIC

    def test_codesize(self):
        import _sre
        assert _sre.getcodesize() == _sre.CODESIZE


class AppTestSrePattern:

    def test_copy(self):
        # copy support is disabled by default in _sre.c
        import re
        p = re.compile("b")
        raises(TypeError, p.__copy__)
        raises(TypeError, p.__deepcopy__)

    def test_creation_attributes(self):
        import re
        pattern_string = "(b)l(?P<g>a)"
        p = re.compile(pattern_string, re.I | re.M)
        assert pattern_string == p.pattern
        assert re.I | re.M == p.flags
        assert 2 == p.groups
        assert {"g": 2} == p.groupindex

    def test_match_none(self):
        import re
        p = re.compile("bla")
        none_matches = ["b", "bl", "blub", "jupidu"]
        for string in none_matches:
            assert None == p.match(string)

    def test_pos_endpos(self):
        import re
        # XXX maybe fancier tests here
        p = re.compile("bl(a)")
        tests = [("abla", 0, 4), ("abla", 1, 4), ("ablaa", 1, 4)]
        for string, pos, endpos in tests:
            assert p.search(string, pos, endpos)
        tests = [("abla", 0, 3), ("abla", 2, 4)]
        for string, pos, endpos in tests:
            assert not p.search(string, pos, endpos)

    def test_findall(self):
        import re
        assert ["b"] == re.findall("b", "bla")
        assert ["a", "u"] == re.findall("b(.)", "abalbus")
        assert [("a", "l"), ("u", "s")] == re.findall("b(.)(.)", "abalbus")
        assert [("a", ""), ("s", "s")] == re.findall("b(a|(s))", "babs")

    def test_finditer(self):
        import re
        it = re.finditer("b(.)", "brabbel")
        assert "br" == it.next().group(0)
        assert "bb" == it.next().group(0)
        raises(StopIteration, it.next)

    def test_split(self):
        import re
        assert ["a", "o", "u", ""] == re.split("b", "abobub")
        assert ["a", "o", "ub"] == re.split("b", "abobub", 2)
        assert ['', 'a', 'l', 'a', 'lla'] == re.split("b(a)", "balballa")
        assert ['', 'a', None, 'l', 'u', None, 'lla'] == (
            re.split("b([ua]|(s))", "balbulla"))


class AppTestSreMatch:

    def test_copy(self):
        import re
        # copy support is disabled by default in _sre.c
        m = re.match("bla", "bla")
        raises(TypeError, m.__copy__)
        raises(TypeError, m.__deepcopy__)

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

    def test_expand(self):
        import re
        m = re.search("a(..)(?P<name>..)", "ab1bc")
        assert "b1bcbc" == m.expand(r"\1\g<name>\2")

    def test_sub(self):
        import re
        assert "bbbbb" == re.sub("a", "b", "ababa")
        assert ("bbbbb", 3) == re.subn("a", "b", "ababa")
        assert "dddd" == re.sub("[abc]", "d", "abcd")
        assert ("dddd", 3) == re.subn("[abc]", "d", "abcd")
        assert "rbd\nbr\n" == re.sub("a(.)", r"b\1\n", "radar")
        assert ("rbd\nbr\n", 2) == re.subn("a(.)", r"b\1\n", "radar")
        assert ("bbbba", 2) == re.subn("a", "b", "ababa", 2)

    def test_sub_unicode(self):
        import re
        assert isinstance(re.sub(u"a", u"b", u""), unicode)
        # the input is returned unmodified if no substitution is performed,
        # which (if interpreted literally, as CPython does) gives the
        # following strangeish rules:
        assert isinstance(re.sub(u"a", u"b", "diwoiioamoi"), unicode)
        assert isinstance(re.sub(u"a", u"b", "diwoiiobmoi"), str)
        assert isinstance(re.sub(u'x', 'y', 'x'), str)

    def test_sub_callable(self):
        import re
        def call_me(match):
            ret = ""
            for char in match.group():
                ret += chr(ord(char) + 1)
            return ret
        assert ("bbbbb", 3) == re.subn("a", call_me, "ababa")

    def test_match_array(self):
        import re, array
        a = array.array('c', 'hello')
        m = re.match('hel+', a)
        assert m.end() == 4

    def test_match_typeerror(self):
        import re
        raises(TypeError, re.match, 'hel+', list('hello'))

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


class AppTestSreScanner:

    def test_scanner_attributes(self):
        import re
        p = re.compile("bla")
        s = p.scanner("blablubla")
        assert p == s.pattern

    def test_scanner_match(self):
        import re
        p = re.compile(".").scanner("bla")
        assert ("b", "l", "a") == (p.match().group(0),
                                    p.match().group(0), p.match().group(0))
        assert None == p.match()

    def test_scanner_search(self):
        import re
        p = re.compile("\d").scanner("bla23c5a")
        assert ("2", "3", "5") == (p.search().group(0),
                                    p.search().group(0), p.search().group(0))
        assert None == p.search()

    def test_scanner_zero_width_match(self):
        import re, sys
        if sys.version_info[:2] == (2, 3):
            return
        p = re.compile(".*").scanner("bla")
        assert ("bla", "") == (p.search().group(0), p.search().group(0))
        assert None == p.search()


class AppTestGetlower:

    def setup_class(cls):
        # This imports support_test_sre as the global "s"
        try:
            cls.space = gettestobjspace(usemodules=('_locale',))
        except Skipped:
            cls.space = gettestobjspace(usemodules=('_rawffi',))
        init_globals_hack(cls.space)

    def setup_method(self, method):
        import locale
        locale.setlocale(locale.LC_ALL, (None, None))
        
    def teardown_method(self, method):
        import locale
        locale.setlocale(locale.LC_ALL, (None, None))

    def test_getlower_no_flags(self):
        UPPER_AE = "\xc4"
        s.assert_lower_equal([("a", "a"), ("A", "a"), (UPPER_AE, UPPER_AE),
            (u"\u00c4", u"\u00c4"), (u"\u4444", u"\u4444")], 0)

    def test_getlower_locale(self):
        import locale, sre_constants
        UPPER_AE = "\xc4"
        LOWER_AE = "\xe4"
        UPPER_PI = u"\u03a0"
        try:
            locale.setlocale(locale.LC_ALL, "de_DE")
            s.assert_lower_equal([("a", "a"), ("A", "a"), (UPPER_AE, LOWER_AE),
                (u"\u00c4", u"\u00e4"), (UPPER_PI, UPPER_PI)],
                sre_constants.SRE_FLAG_LOCALE)
        except locale.Error:
            # skip test
            skip("unsupported locale de_DE")

    def test_getlower_unicode(self):
        import sre_constants
        UPPER_AE = "\xc4"
        LOWER_AE = "\xe4"
        UPPER_PI = u"\u03a0"
        LOWER_PI = u"\u03c0"
        s.assert_lower_equal([("a", "a"), ("A", "a"), (UPPER_AE, LOWER_AE),
            (u"\u00c4", u"\u00e4"), (UPPER_PI, LOWER_PI),
            (u"\u4444", u"\u4444")], sre_constants.SRE_FLAG_UNICODE)
        

class AppTestSimpleSearches:

    def test_search_simple_literal(self):
        import re
        assert re.search("bla", "bla")
        assert re.search("bla", "blab")
        assert not re.search("bla", "blu")

    def test_search_simple_ats(self):
        import re
        assert re.search("^bla", "bla")
        assert re.search("^bla", "blab")
        assert not re.search("^bla", "bbla")
        assert re.search("bla$", "abla")
        assert re.search("bla$", "bla\n")
        assert not re.search("bla$", "blaa")

    def test_search_simple_boundaries(self):
        import re
        UPPER_PI = u"\u03a0"
        assert re.search(r"bla\b", "bla")
        assert re.search(r"bla\b", "bla ja")
        assert re.search(r"bla\b", u"bla%s" % UPPER_PI)
        assert not re.search(r"bla\b", "blano")
        assert not re.search(r"bla\b", u"bla%s" % UPPER_PI, re.UNICODE)

    def test_search_simple_categories(self):
        import re
        LOWER_PI = u"\u03c0"
        INDIAN_DIGIT = u"\u0966"
        EM_SPACE = u"\u2001"
        LOWER_AE = "\xe4"
        assert re.search(r"bla\d\s\w", "bla3 b")
        assert re.search(r"b\d", u"b%s" % INDIAN_DIGIT, re.UNICODE)
        assert not re.search(r"b\D", u"b%s" % INDIAN_DIGIT, re.UNICODE)
        assert re.search(r"b\s", u"b%s" % EM_SPACE, re.UNICODE)
        assert not re.search(r"b\S", u"b%s" % EM_SPACE, re.UNICODE)
        assert re.search(r"b\w", u"b%s" % LOWER_PI, re.UNICODE)
        assert not re.search(r"b\W", u"b%s" % LOWER_PI, re.UNICODE)
        assert re.search(r"b\w", "b%s" % LOWER_AE, re.UNICODE)

    def test_search_simple_any(self):
        import re
        assert re.search(r"b..a", "jboaas")
        assert not re.search(r"b..a", "jbo\nas")
        assert re.search(r"b..a", "jbo\nas", re.DOTALL)

    def test_search_simple_in(self):
        import re
        UPPER_PI = u"\u03a0"
        LOWER_PI = u"\u03c0"
        EM_SPACE = u"\u2001"
        LINE_SEP = u"\u2028"
        assert re.search(r"b[\da-z]a", "bb1a")
        assert re.search(r"b[\da-z]a", "bbsa")
        assert not re.search(r"b[\da-z]a", "bbSa")
        assert re.search(r"b[^okd]a", "bsa")
        assert not re.search(r"b[^okd]a", "bda")
        assert re.search(u"b[%s%s%s]a" % (LOWER_PI, UPPER_PI, EM_SPACE),
            u"b%sa" % UPPER_PI) # bigcharset
        assert re.search(u"b[%s%s%s]a" % (LOWER_PI, UPPER_PI, EM_SPACE),
            u"b%sa" % EM_SPACE)
        assert not re.search(u"b[%s%s%s]a" % (LOWER_PI, UPPER_PI, EM_SPACE),
            u"b%sa" % LINE_SEP)

    def test_search_simple_literal_ignore(self):
        import re
        UPPER_PI = u"\u03a0"
        LOWER_PI = u"\u03c0"
        assert re.search(r"ba", "ba", re.IGNORECASE)
        assert re.search(r"ba", "BA", re.IGNORECASE)
        assert re.search(u"b%s" % UPPER_PI, u"B%s" % LOWER_PI,
            re.IGNORECASE | re.UNICODE)

    def test_search_simple_in_ignore(self):
        import re
        UPPER_PI = u"\u03a0"
        LOWER_PI = u"\u03c0"
        assert re.search(r"ba[A-C]", "bac", re.IGNORECASE)
        assert re.search(r"ba[a-c]", "baB", re.IGNORECASE)
        assert re.search(u"ba[%s]" % UPPER_PI, "ba%s" % LOWER_PI,
            re.IGNORECASE | re.UNICODE)
        assert re.search(r"ba[^A-C]", "bar", re.IGNORECASE)
        assert not re.search(r"ba[^A-C]", "baA", re.IGNORECASE)
        assert not re.search(r"ba[^A-C]", "baa", re.IGNORECASE)

    def test_search_simple_branch(self):
        import re
        assert re.search(r"a(bb|d[ef])b", "adeb")
        assert re.search(r"a(bb|d[ef])b", "abbb")

    def test_search_simple_repeat_one(self):
        import re
        assert re.search(r"aa+", "aa") # empty tail
        assert re.search(r"aa+ab", "aaaab") # backtracking
        assert re.search(r"aa*ab", "aab") # empty match
        assert re.search(r"a[bc]+", "abbccb")
        assert "abbcb" == re.search(r"a.+b", "abbcb\nb").group()
        assert "abbcb\nb" == re.search(r"a.+b", "abbcb\nb", re.DOTALL).group()
        assert re.search(r"ab+c", "aBbBbBc", re.IGNORECASE)
        assert not re.search(r"aa{2,3}", "aa") # string too short
        assert not re.search(r"aa{2,3}b", "aab") # too few repetitions
        assert not re.search(r"aa+b", "aaaac") # tail doesn't match

    def test_search_simple_min_repeat_one(self):
        import re
        assert re.search(r"aa+?", "aa") # empty tail
        assert re.search(r"aa+?ab", "aaaab") # forward tracking
        assert re.search(r"a[bc]+?", "abbccb")
        assert "abb" == re.search(r"a.+?b", "abbcb\nb").group()
        assert "a\nbb" == re.search(r"a.+b", "a\nbbc", re.DOTALL).group()
        assert re.search(r"ab+?c", "aBbBbBc", re.IGNORECASE)
        assert not re.search(r"aa+?", "a") # string too short
        assert not re.search(r"aa{2,3}?b", "aab") # too few repetitions
        assert not re.search(r"aa+?b", "aaaac") # tail doesn't match
        assert re.match(".*?cd", "abcabcde").end(0) == 7

    def test_search_simple_repeat_maximizing(self):
        import re
        assert not re.search(r"(ab){3,5}", "abab")
        assert not re.search(r"(ab){3,5}", "ababa")
        assert re.search(r"(ab){3,5}", "ababab")
        assert re.search(r"(ab){3,5}", "abababababab").end(0) == 10
        assert "ad" == re.search(r"(a.)*", "abacad").group(1)
        assert ("abcg", "cg") == (
            re.search(r"(ab(c.)*)+", "ababcecfabcg").groups())
        assert ("cg", "cg") == (
            re.search(r"(ab|(c.))+", "abcg").groups())
        assert ("ab", "cf") == (
            re.search(r"((c.)|ab)+", "cfab").groups())
        assert re.search(r".*", "")

    def test_search_simple_repeat_minimizing(self):
        import re
        assert not re.search(r"(ab){3,5}?", "abab")
        assert re.search(r"(ab){3,5}?", "ababab")
        assert re.search(r"b(a){3,5}?b", "baaaaab")
        assert not re.search(r"b(a){3,5}?b", "baaaaaab")
        assert re.search(r"a(b(.)+?)*", "abdbebb")

    def test_search_simple_groupref(self):
        import re
        UPPER_PI = u"\u03a0"
        LOWER_PI = u"\u03c0"
        assert re.match(r"((ab)+)c\1", "ababcabab")
        assert not re.match(r"((ab)+)c\1", "ababcab")
        assert not re.search(r"(a|(b))\2", "aa")
        assert re.match(r"((ab)+)c\1", "aBAbcAbaB", re.IGNORECASE)
        assert re.match(r"((a.)+)c\1", u"a%sca%s" % (UPPER_PI, LOWER_PI),
            re.IGNORECASE | re.UNICODE)

    def test_search_simple_groupref_exists(self):
        import re, sys
        if not sys.version_info[:2] == (2, 3):
            assert re.search(r"(<)?bla(?(1)>)", "<bla>")
            assert re.search(r"(<)?bla(?(1)>)", "bla")
            assert not re.match(r"(<)?bla(?(1)>)", "<bla")
            assert re.search(r"(<)?bla(?(1)>|u)", "blau")

    def test_search_simple_assert(self):
        import re
        assert re.search(r"b(?=\d\d).{3,}", "b23a")
        assert not re.search(r"b(?=\d\d).{3,}", "b2aa")
        assert re.search(r"b(?<=\d.)a", "2ba")
        assert not re.search(r"b(?<=\d.)a", "ba")

    def test_search_simple_assert_not(self):
        import re
        assert re.search(r"b(?<!\d.)a", "aba")
        assert re.search(r"b(?<!\d.)a", "ba")
        assert not re.search(r"b(?<!\d.)a", "11ba")

    def test_bug_725149(self):
        # mark_stack_base restoring before restoring marks
        # test copied from CPython test
        import re
        assert re.match('(a)(?:(?=(b)*)c)*', 'abb').groups() == ('a', None)
        assert re.match('(a)((?!(b)*))*', 'abb').groups() == ('a', None, None)


class AppTestMarksStack:

    def test_mark_stack_branch(self):
        import re
        m = re.match("b(.)a|b.b", "bob")
        assert None == m.group(1)
        assert None == m.lastindex

    def test_mark_stack_repeat_one(self):
        import re
        m = re.match("\d+1((2)|(3))4", "2212413")
        assert ("2", "2", None) == m.group(1, 2, 3)
        assert 1 == m.lastindex

    def test_mark_stack_min_repeat_one(self):
        import re
        m = re.match("\d+?1((2)|(3))44", "221341244")
        assert ("2", "2", None) == m.group(1, 2, 3)
        assert 1 == m.lastindex

    def test_mark_stack_max_until(self):
        import re
        m = re.match("(\d)+1((2)|(3))4", "2212413")
        assert ("2", "2", None) == m.group(2, 3, 4)
        assert 2 == m.lastindex

    def test_mark_stack_min_until(self):
        import re
        m = re.match("(\d)+?1((2)|(3))44", "221341244")
        assert ("2", "2", None) == m.group(2, 3, 4)
        assert 2 == m.lastindex
        

class AppTestOpcodes:

    def setup_class(cls):
        try:
            cls.space = gettestobjspace(usemodules=('_locale',))
        except Skipped:
            cls.space = gettestobjspace(usemodules=('_rawffi',))
        # This imports support_test_sre as the global "s"
        init_globals_hack(cls.space)

    def test_length_optimization(self):
        pattern = "bla"
        opcodes = [s.OPCODES["info"], 3, 3, len(pattern)] \
            + s.encode_literal(pattern) + [s.OPCODES["success"]]
        s.assert_no_match(opcodes, ["b", "bl", "ab"])

    def test_literal(self):
        opcodes = s.encode_literal("bla") + [s.OPCODES["success"]]
        s.assert_no_match(opcodes, ["bl", "blu"])
        s.assert_match(opcodes, ["bla", "blab", "cbla", "bbla"])

    def test_not_literal(self):
        opcodes = s.encode_literal("b") \
            + [s.OPCODES["not_literal"], ord("a"), s.OPCODES["success"]]
        s.assert_match(opcodes, ["bx", "ababy"])
        s.assert_no_match(opcodes, ["ba", "jabadu"])

    def test_unknown(self):
        raises(RuntimeError, s.search, [55555], "b")

    def test_at_beginning(self):
        for atname in ["at_beginning", "at_beginning_string"]:
            opcodes = [s.OPCODES["at"], s.ATCODES[atname]] \
                + s.encode_literal("bla") + [s.OPCODES["success"]]
            s.assert_match(opcodes, "bla")
            s.assert_no_match(opcodes, "abla")

    def test_at_beginning_line(self):
        opcodes = [s.OPCODES["at"], s.ATCODES["at_beginning_line"]] \
            + s.encode_literal("bla") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["bla", "x\nbla"])
        s.assert_no_match(opcodes, ["abla", "abla\nubla"])

    def test_at_end(self):
        opcodes = s.encode_literal("bla") \
            + [s.OPCODES["at"], s.ATCODES["at_end"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["bla", "bla\n"])
        s.assert_no_match(opcodes, ["blau", "abla\nblau"])

    def test_at_end_line(self):
        opcodes = s.encode_literal("bla") \
            + [s.OPCODES["at"], s.ATCODES["at_end_line"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["bla\n", "bla\nx", "bla"])
        s.assert_no_match(opcodes, ["blau"])

    def test_at_end_string(self):
        opcodes = s.encode_literal("bla") \
            + [s.OPCODES["at"], s.ATCODES["at_end_string"], s.OPCODES["success"]]
        s.assert_match(opcodes, "bla")
        s.assert_no_match(opcodes, ["blau", "bla\n"])

    def test_at_boundary(self):
        for atname in "at_boundary", "at_loc_boundary", "at_uni_boundary":
            opcodes = s.encode_literal("bla") \
                + [s.OPCODES["at"], s.ATCODES[atname], s.OPCODES["success"]]
            s.assert_match(opcodes, ["bla", "bla ha", "bla,x"])
            s.assert_no_match(opcodes, ["blaja", ""])
            opcodes = [s.OPCODES["at"], s.ATCODES[atname]] \
                + s.encode_literal("bla") + [s.OPCODES["success"]]
            s.assert_match(opcodes, "bla")
            s.assert_no_match(opcodes, "")

    def test_at_non_boundary(self):
        for atname in "at_non_boundary", "at_loc_non_boundary", "at_uni_non_boundary":
            opcodes = s.encode_literal("bla") \
                + [s.OPCODES["at"], s.ATCODES[atname], s.OPCODES["success"]]
            s.assert_match(opcodes, "blan")
            s.assert_no_match(opcodes, ["bla ja", "bla"])

    def test_at_loc_boundary(self):
        import locale
        try:
            s.void_locale()
            opcodes1 = s.encode_literal("bla") \
                + [s.OPCODES["at"], s.ATCODES["at_loc_boundary"], s.OPCODES["success"]]
            opcodes2 = s.encode_literal("bla") \
                + [s.OPCODES["at"], s.ATCODES["at_loc_non_boundary"], s.OPCODES["success"]]
            s.assert_match(opcodes1, "bla\xFC")
            s.assert_no_match(opcodes2, "bla\xFC")
            locale.setlocale(locale.LC_ALL, "de_DE")
            s.assert_no_match(opcodes1, "bla\xFC")
            s.assert_match(opcodes2, "bla\xFC")
            locale.resetlocale() # is this the right way to rest the locale?
        except locale.Error:
            # skip test
            skip("locale error")

    def test_at_uni_boundary(self):
        UPPER_PI = u"\u03a0"
        LOWER_PI = u"\u03c0"
        opcodes = s.encode_literal("bl") + [s.OPCODES["any"], s.OPCODES["at"],
            s.ATCODES["at_uni_boundary"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["bla ha", u"bl%s ja" % UPPER_PI])
        s.assert_no_match(opcodes, [u"bla%s" % LOWER_PI])
        opcodes = s.encode_literal("bl") + [s.OPCODES["any"], s.OPCODES["at"],
            s.ATCODES["at_uni_non_boundary"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["blaha", u"bl%sja" % UPPER_PI])

    def test_category_digit(self):
        INDIAN_DIGIT = u"\u0966"
        opcodes = [s.OPCODES["category"], s.CHCODES["category_digit"]] \
            + s.encode_literal("b") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["1b", "a1b"])
        s.assert_no_match(opcodes, ["bb", "b1", u"%sb" % INDIAN_DIGIT])

    def test_category_not_digit(self):
        INDIAN_DIGIT = u"\u0966"
        opcodes = [s.OPCODES["category"], s.CHCODES["category_not_digit"]] \
            + s.encode_literal("b") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["bb", "1ab", u"%sb" % INDIAN_DIGIT])
        s.assert_no_match(opcodes, ["1b", "a1b"])

    def test_category_space(self):
        EM_SPACE = u"\u2001"
        opcodes = s.encode_literal("b") \
             + [s.OPCODES["category"], s.CHCODES["category_space"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["b ", "b\n", "b\t", "b\r", "b\v", "b\f"])
        s.assert_no_match(opcodes, ["bb", "b1", u"b%s" % EM_SPACE])

    def test_category_not_space(self):
        EM_SPACE = u"\u2001"
        opcodes = s.encode_literal("b") \
             + [s.OPCODES["category"], s.CHCODES["category_not_space"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["bb", "b1", u"b%s" % EM_SPACE])
        s.assert_no_match(opcodes, ["b ", "b\n", "b\t", "b\r", "b\v", "b\f"])

    def test_category_word(self):
        LOWER_PI = u"\u03c0"
        opcodes = s.encode_literal("b") \
             + [s.OPCODES["category"], s.CHCODES["category_word"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["bl", "b4", "b_"])
        s.assert_no_match(opcodes, ["b ", "b\n", u"b%s" % LOWER_PI])

    def test_category_not_word(self):
        LOWER_PI = u"\u03c0"
        opcodes = s.encode_literal("b") \
             + [s.OPCODES["category"], s.CHCODES["category_not_word"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["b ", "b\n", u"b%s" % LOWER_PI])
        s.assert_no_match(opcodes, ["bl", "b4", "b_"])

    def test_category_linebreak(self):
        LINE_SEP = u"\u2028"
        opcodes = s.encode_literal("b") \
             + [s.OPCODES["category"], s.CHCODES["category_linebreak"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["b\n"])
        s.assert_no_match(opcodes, ["b ", "bs", "b\r", u"b%s" % LINE_SEP])
        opcodes = s.encode_literal("b") \
             + [s.OPCODES["category"], s.CHCODES["category_uni_linebreak"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["b\n", u"b%s" % LINE_SEP])

    def test_category_not_linebreak(self):
        LINE_SEP = u"\u2028"
        opcodes = s.encode_literal("b") \
             + [s.OPCODES["category"], s.CHCODES["category_not_linebreak"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["b ", "bs", u"b%s" % LINE_SEP])
        s.assert_no_match(opcodes, ["b\n"])
        opcodes = s.encode_literal("b") \
             + [s.OPCODES["category"], s.CHCODES["category_uni_not_linebreak"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["b ", "bs"])
        s.assert_no_match(opcodes, ["b\n", u"b%s" % LINE_SEP, "b\r"])

    def test_category_loc_word(self):
        import locale
        try:
            s.void_locale()
            opcodes1 = s.encode_literal("b") \
                + [s.OPCODES["category"], s.CHCODES["category_loc_word"], s.OPCODES["success"]]
            opcodes2 = s.encode_literal("b") \
                + [s.OPCODES["category"], s.CHCODES["category_loc_not_word"], s.OPCODES["success"]]
            s.assert_no_match(opcodes1, "b\xFC")
            s.assert_no_match(opcodes1, u"b\u00FC")
            s.assert_match(opcodes2, "b\xFC")
            locale.setlocale(locale.LC_ALL, "de_DE")
            s.assert_match(opcodes1, "b\xFC")
            s.assert_no_match(opcodes1, u"b\u00FC")
            s.assert_no_match(opcodes2, "b\xFC")
            s.void_locale()
        except locale.Error:
            # skip test
            skip("locale error")

    def test_any(self):
        opcodes = s.encode_literal("b") + [s.OPCODES["any"]] \
            + s.encode_literal("a") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["b a", "bla", "bboas"])
        s.assert_no_match(opcodes, ["b\na", "oba", "b"])

    def test_any_all(self):
        opcodes = s.encode_literal("b") + [s.OPCODES["any_all"]] \
            + s.encode_literal("a") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["b a", "bla", "bboas", "b\na"])
        s.assert_no_match(opcodes, ["oba", "b"])

    def test_in_failure(self):
        opcodes = s.encode_literal("b") + [s.OPCODES["in"], 2, s.OPCODES["failure"]] \
            + s.encode_literal("a") + [s.OPCODES["success"]]
        s.assert_no_match(opcodes, ["ba", "bla"])

    def test_in_literal(self):
        opcodes = s.encode_literal("b") + [s.OPCODES["in"], 7] \
            + s.encode_literal("la") + [s.OPCODES["failure"], s.OPCODES["failure"]] \
            + s.encode_literal("a") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["bla", "baa", "blbla"])
        s.assert_no_match(opcodes, ["ba", "bja", "blla"])

    def test_in_category(self):
        opcodes = s.encode_literal("b") + [s.OPCODES["in"], 6, s.OPCODES["category"],
            s.CHCODES["category_digit"], s.OPCODES["category"], s.CHCODES["category_space"],
            s.OPCODES["failure"]] + s.encode_literal("a") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["b1a", "b a", "b4b\tas"])
        s.assert_no_match(opcodes, ["baa", "b5"])

    def test_in_charset_ucs2(self):
        import _sre
        if _sre.CODESIZE != 2:
            return
        # charset bitmap for characters "l" and "h"
        bitmap = 6 * [0] + [4352] + 9 * [0]
        opcodes = s.encode_literal("b") + [s.OPCODES["in"], 19, s.OPCODES["charset"]] \
            + bitmap + [s.OPCODES["failure"]] + s.encode_literal("a") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["bla", "bha", "blbha"])
        s.assert_no_match(opcodes, ["baa", "bl"])

    def _test_in_bigcharset_ucs2(self):
        # disabled because this actually only works on big-endian machines
        if _sre.CODESIZE != 2:
            return
        # constructing bigcharset for lowercase pi (\u03c0)
        UPPER_PI = u"\u03a0"
        LOWER_PI = u"\u03c0"
        bitmap = 6 * [0] + [4352] + 9 * [0]
        opcodes = s.encode_literal("b") + [s.OPCODES["in"], 164, s.OPCODES["bigcharset"], 2] \
            + [0, 1] + 126 * [0] \
            + 16 * [0] \
            + 12 * [0] + [1] + 3 * [0] \
            + [s.OPCODES["failure"]] + s.encode_literal("a") + [s.OPCODES["success"]]
        s.assert_match(opcodes, [u"b%sa" % LOWER_PI])
        s.assert_no_match(opcodes, [u"b%sa" % UPPER_PI])

    # XXX bigcharset test for ucs4 missing here

    def test_in_range(self):
        opcodes = s.encode_literal("b") + [s.OPCODES["in"], 5, s.OPCODES["range"],
            ord("1"), ord("9"), s.OPCODES["failure"]] \
            + s.encode_literal("a") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["b1a", "b56b7aa"])
        s.assert_no_match(opcodes, ["baa", "b5"])

    def test_in_negate(self):
        opcodes = s.encode_literal("b") + [s.OPCODES["in"], 7, s.OPCODES["negate"]] \
            + s.encode_literal("la") + [s.OPCODES["failure"]] \
            + s.encode_literal("a") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["b1a", "bja", "bubua"])
        s.assert_no_match(opcodes, ["bla", "baa", "blbla"])

    def test_literal_ignore(self):
        opcodes = s.encode_literal("b") \
            + [s.OPCODES["literal_ignore"], ord("a"), s.OPCODES["success"]]
        s.assert_match(opcodes, ["ba", "bA"])
        s.assert_no_match(opcodes, ["bb", "bu"])

    def test_not_literal_ignore(self):
        UPPER_PI = u"\u03a0"
        opcodes = s.encode_literal("b") \
            + [s.OPCODES["not_literal_ignore"], ord("a"), s.OPCODES["success"]]
        s.assert_match(opcodes, ["bb", "bu", u"b%s" % UPPER_PI])
        s.assert_no_match(opcodes, ["ba", "bA"])

    def test_in_ignore(self):
        opcodes = s.encode_literal("b") + [s.OPCODES["in_ignore"], 8] \
            + s.encode_literal("abc") + [s.OPCODES["failure"]] \
            + s.encode_literal("a") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["baa", "bAa", "bbbBa"])
        s.assert_no_match(opcodes, ["ba", "bja", "blla"])

    def test_in_jump_info(self):
        for opname in "jump", "info":
            opcodes = s.encode_literal("b") \
                + [s.OPCODES[opname], 3, s.OPCODES["failure"], s.OPCODES["failure"]] \
                + s.encode_literal("a") + [s.OPCODES["success"]]
            s.assert_match(opcodes, "ba")

    def _test_mark(self):
        # XXX need to rewrite this implementation-independent
        opcodes = s.encode_literal("a") + [s.OPCODES["mark"], 0] \
            + s.encode_literal("b") + [s.OPCODES["mark"], 1, s.OPCODES["success"]]
        state = self.create_state("abc")
        _sre._sre_search(state, opcodes)
        assert 1 == state.lastindex
        assert 1 == state.lastmark
        # NB: the following are indexes from the start of the match
        assert [1, 2] == state.marks

    def test_branch(self):
        opcodes = [s.OPCODES["branch"], 7] + s.encode_literal("ab") \
            + [s.OPCODES["jump"], 9, 7] + s.encode_literal("cd") \
            + [s.OPCODES["jump"], 2, s.OPCODES["failure"], s.OPCODES["success"]]
        s.assert_match(opcodes, ["ab", "cd"])
        s.assert_no_match(opcodes, ["aacas", "ac", "bla"])

    def test_repeat_one(self):
        opcodes = [s.OPCODES["repeat_one"], 6, 1, 65535] + s.encode_literal("a") \
            + [s.OPCODES["success"]] + s.encode_literal("ab") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["aab", "aaaab"])
        s.assert_no_match(opcodes, ["ab", "a"])

    def test_min_repeat_one(self):
        opcodes = [s.OPCODES["min_repeat_one"], 5, 1, 65535, s.OPCODES["any"]] \
            + [s.OPCODES["success"]] + s.encode_literal("b") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["aab", "ardb", "bb"])
        s.assert_no_match(opcodes, ["b"])

    def test_repeat_maximizing(self):
        opcodes = [s.OPCODES["repeat"], 5, 1, 65535] + s.encode_literal("a") \
            + [s.OPCODES["max_until"]] + s.encode_literal("b") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["ab", "aaaab", "baabb"])
        s.assert_no_match(opcodes, ["aaa", "", "ac"])

    def test_max_until_error(self):
        opcodes = [s.OPCODES["max_until"], s.OPCODES["success"]]
        raises(RuntimeError, s.search, opcodes, "a")

    def test_max_until_zero_width_match(self):
        # re.compile won't compile prospective zero-with matches (all of them?),
        # so we can only produce an example by directly constructing bytecodes.
        # CPython 2.3 fails with a recursion limit exceeded error here.
        import sys
        if not sys.version_info[:2] == (2, 3):
            opcodes = [s.OPCODES["repeat"], 10, 1, 65535, s.OPCODES["repeat_one"],
                6, 0, 65535] + s.encode_literal("a") + [s.OPCODES["success"],
                s.OPCODES["max_until"], s.OPCODES["success"]]
            s.assert_match(opcodes, ["ab", "bb"])
            assert "" == s.search(opcodes, "bb").group(0)

    def test_repeat_minimizing(self):
        opcodes = [s.OPCODES["repeat"], 4, 1, 65535, s.OPCODES["any"],
            s.OPCODES["min_until"]] + s.encode_literal("b") + [s.OPCODES["success"]]
        s.assert_match(opcodes, ["ab", "aaaab", "baabb"])
        s.assert_no_match(opcodes, ["b"])
        assert "aab" == s.search(opcodes, "aabb").group(0)

    def test_min_until_error(self):
        opcodes = [s.OPCODES["min_until"], s.OPCODES["success"]]
        raises(RuntimeError, s.search, opcodes, "a")

    def test_groupref(self):
        opcodes = [s.OPCODES["mark"], 0, s.OPCODES["any"], s.OPCODES["mark"], 1] \
            + s.encode_literal("a") + [s.OPCODES["groupref"], 0, s.OPCODES["success"]]
        s.assert_match(opcodes, ["bab", "aaa", "dad"])
        s.assert_no_match(opcodes, ["ba", "bad", "baad"])

    def test_groupref_ignore(self):
        opcodes = [s.OPCODES["mark"], 0, s.OPCODES["any"], s.OPCODES["mark"], 1] \
            + s.encode_literal("a") + [s.OPCODES["groupref_ignore"], 0, s.OPCODES["success"]]
        s.assert_match(opcodes, ["bab", "baB", "Dad"])
        s.assert_no_match(opcodes, ["ba", "bad", "baad"])

    def test_assert(self):
        opcodes = s.encode_literal("a") + [s.OPCODES["assert"], 4, 0] \
            + s.encode_literal("b") + [s.OPCODES["success"], s.OPCODES["success"]]
        assert "a" == s.search(opcodes, "ab").group(0)
        s.assert_no_match(opcodes, ["a", "aa"])

    def test_assert_not(self):
        opcodes = s.encode_literal("a") + [s.OPCODES["assert_not"], 4, 0] \
            + s.encode_literal("b") + [s.OPCODES["success"], s.OPCODES["success"]]
        assert "a" == s.search(opcodes, "ac").group(0)
        s.assert_match(opcodes, ["a"])
        s.assert_no_match(opcodes, ["ab"])

    def test_bug(self):
        import re
        assert re.sub('=\w{2}', 'x', '=CA') == 'x'

class AppTestOptimizations:
    """These tests try to trigger optmized edge cases."""

    def test_match_length_optimization(self):
        import re
        assert None == re.match("bla", "blub")

    def test_fast_search(self):
        import re
        assert None == re.search("bl", "abaub")
        assert None == re.search("bl", "b")
        assert ["bl", "bl"] == re.findall("bl", "blbl")
        assert ["a", "u"] == re.findall("bl(.)", "blablu")

    def test_branch_literal_shortcut(self):
        import re
        assert None == re.search("bl|a|c", "hello")

    def test_literal_search(self):
        import re
        assert re.search("b(\d)", "ababbbab1")
        assert None == re.search("b(\d)", "ababbbab")

    def test_repeat_one_literal_tail(self):
        import re
        assert re.search(".+ab", "wowowowawoabwowo")
        assert None == re.search(".+ab", "wowowaowowo")
