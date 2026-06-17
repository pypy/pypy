# spaceconfig = {"usemodules": ["array", "itertools"]}

import pytest


# ---------------------------------------------------------------------------
# Buffer-protocol / export lifetime tests (original apptest_sre.py content)
# ---------------------------------------------------------------------------

def test_finditer_holds_bytearray_export():
    # A live finditer iterator must lock the bytearray (prevent resize).
    import re, gc
    b = bytearray(b'aaa')
    it = re.finditer(b'a', b)
    try:
        b.extend(b'x')
    except BufferError:
        pass
    else:
        raise AssertionError("expected BufferError while iterator alive")
    list(it)   # exhaust -> eager release
    del it
    gc.collect()
    b.extend(b'x')   # must succeed after exhaustion


def test_scanner_dropped_releases_bytearray_export():
    # Bug 1: W_SRE_Scanner defines _finalize_ but never calls
    # register_finalizer.  Dropping a mid-iteration scanner therefore leaks
    # _exports and leaves the bytearray permanently locked.
    import re, gc
    b = bytearray(b'aaa')
    it = re.finditer(b'a', b)
    next(it)    # consume one match; eager path only fires on exhaustion

    try:
        b.extend(b'x')   # must raise: iterator still alive
    except BufferError:
        pass
    else:
        raise AssertionError("expected BufferError while iterator alive")

    del it
    gc.collect()
    gc.collect()   # FinalizerQueue may need a second cycle
    b.extend(b'x')   # must NOT raise: GC must have released the export


# ---------------------------------------------------------------------------
# AppTestSrePy
# ---------------------------------------------------------------------------

def test_magic():
    import _sre, sre_constants
    assert sre_constants.MAGIC == _sre.MAGIC


def test_codesize():
    import _sre
    assert _sre.getcodesize() == _sre.CODESIZE
    assert _sre.CODESIZE == 4


def test_opcodes():
    import _sre
    assert _sre.OPCODES[:4] == 'failure success any any_all'.split()


# ---------------------------------------------------------------------------
# AppTestSrePattern
# ---------------------------------------------------------------------------

def test_pattern_copy():
    import re
    p = re.compile("b")
    assert p.__copy__() is p
    assert p.__deepcopy__("whatever") is p


def test_creation_attributes():
    import re
    pattern_string = b"(b)l(?P<g>a)"
    p = re.compile(pattern_string, re.I | re.M)
    assert pattern_string == p.pattern
    assert re.I | re.M == p.flags
    assert 2 == p.groups
    assert {"g": 2} == p.groupindex
    with pytest.raises(TypeError):
        p.groupindex['g'] = 3


def test_repeat_minmax_overflow():
    import re, sre_constants
    string = "x" * 100000
    assert re.match(r".{%d}" % (sre_constants.MAXREPEAT - 1), string) is None
    assert re.match(r".{,%d}" % (sre_constants.MAXREPEAT - 1), string).span() == (0, 100000)
    assert re.match(r".{%d,}?" % (sre_constants.MAXREPEAT - 1), string) is None
    pytest.raises(OverflowError, re.compile, r".{%d}" % sre_constants.MAXREPEAT)
    pytest.raises(OverflowError, re.compile, r".{,%d}" % sre_constants.MAXREPEAT)
    pytest.raises(OverflowError, re.compile, r".{%d,}?" % sre_constants.MAXREPEAT)


def test_match_none():
    import re
    p = re.compile("bla")
    none_matches = ["b", "bl", "blub", "jupidu"]
    for string in none_matches:
        assert None == p.match(string)


def test_pos_endpos():
    import re
    p = re.compile("bl(a)")
    tests = [("abla", 0, 4), ("abla", 1, 4), ("ablaa", 1, 4)]
    for string, pos, endpos in tests:
        assert p.search(string, pos, endpos)
    tests = [("abla", 0, 3), ("abla", 2, 4)]
    for string, pos, endpos in tests:
        assert not p.search(string, pos, endpos)


def test_findall():
    import re
    assert ["b"] == re.findall("b", "bla")
    assert ["a", "u"] == re.findall("b(.)", "abalbus")
    assert [("a", "l"), ("u", "s")] == re.findall("b(.)(.)", "abalbus")
    assert [("a", ""), ("s", "s")] == re.findall("b(a|(s))", "babs")
    assert ['', '', 'X', '', ''] == re.findall("X??", "1X4")


def test_findall_unicode():
    import re
    assert [u"\u1234"] == re.findall(u"\u1234", u"\u1000\u1234\u2000")
    assert ["a", "u"] == re.findall("b(.)", "abalbus")
    assert [("a", "l"), ("u", "s")] == re.findall("b(.)(.)", "abalbus")
    assert [("a", ""), ("s", "s")] == re.findall("b(a|(s))", "babs")
    assert [(b"a", b""), (b"s", b"s")] == re.findall(b"b(a|(s))", b"babs")
    assert [u"xyz"] == re.findall(u".*yz", u"xyz")


def test_finditer():
    import re
    it = re.finditer("b(.)", "brabbel")
    assert "br" == next(it).group(0)
    assert "bb" == next(it).group(0)
    pytest.raises(StopIteration, next, it)


def test_split():
    import re
    assert ["a", "o", "u", ""] == re.split("b", "abobub")
    assert ["a", "o", "ub"] == re.split("b", "abobub", 2)
    assert ['', 'a', 'l', 'a', 'lla'] == re.split("b(a)", "balballa")
    assert ['', 'a', None, 'l', 'u', None, 'lla'] == (
        re.split("b([ua]|(s))", "balbulla"))
    assert ['Hello \udce2\udc9c\udc93', ''] == re.split(r'\r\n|\r|\n',
                'Hello \udce2\udc9c\udc93\n')


def test_weakref():
    import re, _weakref
    _weakref.ref(re.compile(r""))


def test_match_compat():
    import re
    res = re.match(r'(a)|(b)', 'b').start(1)
    assert res == -1


def test_pattern_check():
    import _sre
    pytest.raises(TypeError, _sre.compile, {}, 0, [])


def test_fullmatch():
    import re
    assert re.compile(r"ab*c").fullmatch("abbcdef") is None
    assert re.compile(r"ab*c").fullmatch("abbc") is not None
    assert re.fullmatch(r"ab*c", "abbbcdef") is None
    assert re.fullmatch(r"ab*c", "abbbc") is not None


def test_pattern_repr():
    import re
    r = re.compile(r'f(o"\d)', 0)
    assert repr(r) == (
        r"""re.compile('f(o"\\d)')""")
    r = re.compile(r'f(o"\d)', re.IGNORECASE|re.DOTALL|re.VERBOSE)
    assert repr(r) == (
        r"""re.compile('f(o"\\d)', re.IGNORECASE|re.DOTALL|re.VERBOSE)""")


def test_pattern_compare():
    import re
    pattern1 = re.compile('abc', re.IGNORECASE)

    assert pattern1 == pattern1
    assert not(pattern1 != pattern1)
    re.purge()
    pattern2 = re.compile('abc', re.IGNORECASE)
    assert hash(pattern2) == hash(pattern1)
    assert pattern2 == pattern1

    re.purge()
    pattern3 = re.compile('XYZ', re.IGNORECASE)
    assert pattern3 != pattern1

    re.purge()
    pattern4 = re.compile('abc')
    assert pattern4 != pattern1

    with pytest.raises(TypeError):
        pattern1 < pattern2


# ---------------------------------------------------------------------------
# AppTestSreScanner
# ---------------------------------------------------------------------------

def test_scanner_attributes():
    import re
    p = re.compile("bla")
    s = p.scanner("blablubla")
    assert p == s.pattern


def test_scanner_match():
    import re
    p = re.compile(".").scanner("bla")
    assert ("b", "l", "a") == (p.match().group(0),
                                p.match().group(0), p.match().group(0))
    assert None == p.match()


def test_scanner_match_detail():
    import re
    p = re.compile("a").scanner("aaXaa")
    assert "a" == p.match().group(0)
    assert "a" == p.match().group(0)
    assert None == p.match()
    assert None == p.match()
    assert None == p.match()


def test_scanner_search():
    import re
    p = re.compile(r"\d").scanner("bla23c5a")
    assert ("2", "3", "5") == (p.search().group(0),
                                p.search().group(0), p.search().group(0))
    assert None == p.search()


def test_scanner_zero_width_match():
    import re
    p = re.compile(".*").scanner("bla")
    assert ("bla", "") == (p.search().group(0), p.search().group(0))
    assert None == p.search()


def test_scanner_empty_match():
    import re
    p = re.compile("a??").scanner("bac")
    assert ("", "", "a", "", "") == (
        p.search().group(0), p.search().group(0), p.search().group(0),
        p.search().group(0), p.search().group(0))
    assert None == p.search()


def test_no_pattern():
    import sre_compile, sre_parse
    sre_pattern = sre_compile.compile(
        sre_parse.SubPattern(sre_parse.State()))
    assert sre_pattern.scanner('s') is not None


def test_scanner_match_string():
    import re
    class mystr(type(u"")):
        pass
    s = mystr(u"bla")
    p = re.compile(u".").scanner(s)
    m = p.match()
    assert m.string is s


# ---------------------------------------------------------------------------
# AppTestSimpleSearches
# ---------------------------------------------------------------------------

def test_search_simple_literal():
    import re
    assert re.search("bla", "bla")
    assert re.search("bla", "blab")
    assert not re.search("bla", "blu")


def test_search_simple_ats():
    import re
    assert re.search("^bla", "bla")
    assert re.search("^bla", "blab")
    assert not re.search("^bla", "bbla")
    assert re.search("bla$", "abla")
    assert re.search("bla$", "bla\n")
    assert not re.search("bla$", "blaa")


def test_search_simple_boundaries():
    import re
    UPPER_PI = "\u03a0"
    assert re.search(r"bla\b", "bla")
    assert re.search(r"bla\b", "bla ja")
    assert re.search(r"bla\b", "bla%s" % UPPER_PI, re.ASCII)
    assert not re.search(r"bla\b", "blano")
    assert not re.search(r"bla\b", "bla%s" % UPPER_PI, re.UNICODE)


def test_search_simple_categories():
    import re
    LOWER_PI = "\u03c0"
    INDIAN_DIGIT = "\u0966"
    EM_SPACE = "\u2001"
    LOWER_AE = "\xe4"
    assert re.search(r"bla\d\s\w", "bla3 b")
    assert re.search(r"b\d", "b%s" % INDIAN_DIGIT, re.UNICODE)
    assert not re.search(r"b\D", "b%s" % INDIAN_DIGIT, re.UNICODE)
    assert re.search(r"b\s", "b%s" % EM_SPACE, re.UNICODE)
    assert not re.search(r"b\S", "b%s" % EM_SPACE, re.UNICODE)
    assert re.search(r"b\w", "b%s" % LOWER_PI, re.UNICODE)
    assert not re.search(r"b\W", "b%s" % LOWER_PI, re.UNICODE)
    assert re.search(r"b\w", "b%s" % LOWER_AE, re.UNICODE)


def test_search_simple_any():
    import re
    assert re.search(r"b..a", "jboaas")
    assert not re.search(r"b..a", "jbo\nas")
    assert re.search(r"b..a", "jbo\nas", re.DOTALL)


def test_search_simple_in():
    import re
    UPPER_PI = "\u03a0"
    LOWER_PI = "\u03c0"
    EM_SPACE = "\u2001"
    LINE_SEP = "\u2028"
    assert re.search(r"b[\da-z]a", "bb1a")
    assert re.search(r"b[\da-z]a", "bbsa")
    assert not re.search(r"b[\da-z]a", "bbSa")
    assert re.search(r"b[^okd]a", "bsa")
    assert not re.search(r"b[^okd]a", "bda")
    assert re.search("b[%s%s%s]a" % (LOWER_PI, UPPER_PI, EM_SPACE),
        "b%sa" % UPPER_PI)
    assert re.search("b[%s%s%s]a" % (LOWER_PI, UPPER_PI, EM_SPACE),
        "b%sa" % EM_SPACE)
    assert not re.search("b[%s%s%s]a" % (LOWER_PI, UPPER_PI, EM_SPACE),
        "b%sa" % LINE_SEP)


def test_search_simple_literal_ignore():
    import re
    UPPER_PI = "\u03a0"
    LOWER_PI = "\u03c0"
    assert re.search(r"ba", "ba", re.IGNORECASE)
    assert re.search(r"ba", "BA", re.IGNORECASE)
    assert re.search("b%s" % UPPER_PI, "B%s" % LOWER_PI,
        re.IGNORECASE | re.UNICODE)


def test_search_simple_in_ignore():
    import re
    UPPER_PI = "\u03a0"
    LOWER_PI = "\u03c0"
    assert re.search(r"ba[A-C]", "bac", re.IGNORECASE)
    assert re.search(r"ba[a-c]", "baB", re.IGNORECASE)
    assert re.search("ba[%s]" % UPPER_PI, "ba%s" % LOWER_PI,
        re.IGNORECASE | re.UNICODE)
    assert re.search(r"ba[^A-C]", "bar", re.IGNORECASE)
    assert not re.search(r"ba[^A-C]", "baA", re.IGNORECASE)
    assert not re.search(r"ba[^A-C]", "baa", re.IGNORECASE)


def test_search_simple_branch():
    import re
    assert re.search(r"a(bb|d[ef])b", "adeb")
    assert re.search(r"a(bb|d[ef])b", "abbb")


def test_search_simple_repeat_one():
    import re
    assert re.search(r"aa+", "aa")
    assert re.search(r"aa+ab", "aaaab")
    assert re.search(r"aa*ab", "aab")
    assert re.search(r"a[bc]+", "abbccb")
    assert "abbcb" == re.search(r"a.+b", "abbcb\nb").group()
    assert "abbcb\nb" == re.search(r"a.+b", "abbcb\nb", re.DOTALL).group()
    assert re.search(r"ab+c", "aBbBbBc", re.IGNORECASE)
    assert not re.search(r"aa{2,3}", "aa")
    assert not re.search(r"aa{2,3}b", "aab")
    assert not re.search(r"aa+b", "aaaac")


def test_search_simple_min_repeat_one():
    import re
    assert re.search(r"aa+?", "aa")
    assert re.search(r"aa+?ab", "aaaab")
    assert re.search(r"a[bc]+?", "abbccb")
    assert "abb" == re.search(r"a.+?b", "abbcb\nb").group()
    assert "a\nbb" == re.search(r"a.+b", "a\nbbc", re.DOTALL).group()
    assert re.search(r"ab+?c", "aBbBbBc", re.IGNORECASE)
    assert not re.search(r"aa+?", "a")
    assert not re.search(r"aa{2,3}?b", "aab")
    assert not re.search(r"aa+?b", "aaaac")
    assert re.match(".*?cd", "abcabcde").end(0) == 7


def test_search_simple_repeat_maximizing():
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


def test_search_simple_repeat_minimizing():
    import re
    assert not re.search(r"(ab){3,5}?", "abab")
    assert re.search(r"(ab){3,5}?", "ababab")
    assert re.search(r"b(a){3,5}?b", "baaaaab")
    assert not re.search(r"b(a){3,5}?b", "baaaaaab")
    assert re.search(r"a(b(.)+?)*", "abdbebb")



def test_search_simple_groupref_exists():
    import re
    assert re.search(r"(<)?bla(?(1)>)", "<bla>")
    assert re.search(r"(<)?bla(?(1)>)", "bla")
    assert not re.match(r"(<)?bla(?(1)>)", "<bla")
    assert re.search(r"(<)?bla(?(1)>|u)", "blau")


def test_search_simple_assert():
    import re
    assert re.search(r"b(?=\d\d).{3,}", "b23a")
    assert not re.search(r"b(?=\d\d).{3,}", "b2aa")
    assert re.search(r"b(?<=\d.)a", "2ba")
    assert not re.search(r"b(?<=\d.)a", "ba")


def test_search_simple_assert_not():
    import re
    assert re.search(r"b(?<!\d.)a", "aba")
    assert re.search(r"b(?<!\d.)a", "ba")
    assert not re.search(r"b(?<!\d.)a", "11ba")


# ---------------------------------------------------------------------------
# AppTestMarksStack
# ---------------------------------------------------------------------------

def test_mark_stack_branch():
    import re
    m = re.match("b(.)a|b.b", "bob")
    assert None == m.group(1)
    assert None == m.lastindex


def test_mark_stack_repeat_one():
    import re
    m = re.match(r"\d+1((2)|(3))4", "2212413")
    assert ("2", "2", None) == m.group(1, 2, 3)
    assert 1 == m.lastindex


def test_mark_stack_min_repeat_one():
    import re
    m = re.match(r"\d+?1((2)|(3))44", "221341244")
    assert ("2", "2", None) == m.group(1, 2, 3)
    assert 1 == m.lastindex


def test_mark_stack_max_until():
    import re
    m = re.match(r"(\d)+1((2)|(3))4", "2212413")
    assert ("2", "2", None) == m.group(2, 3, 4)
    assert 2 == m.lastindex


def test_mark_stack_min_until():
    import re
    m = re.match(r"(\d)+?1((2)|(3))44", "221341244")
    assert ("2", "2", None) == m.group(2, 3, 4)
    assert 2 == m.lastindex


def test_bug_725149():
    import re
    assert re.match('(a)(?:(?=(b)*)c)*', 'abb').groups() == ('a', None)
    assert re.match('(a)((?!(b)*))*', 'abb').groups() == ('a', None, None)


# ---------------------------------------------------------------------------
# AppTestOptimizations
# ---------------------------------------------------------------------------

def test_match_length_optimization():
    import re
    assert None == re.match("bla", "blub")


def test_fast_search():
    import re
    assert None == re.search("bl", "abaub")
    assert None == re.search("bl", "b")
    assert ["bl", "bl"] == re.findall("bl", "blbl")
    assert ["a", "u"] == re.findall("bl(.)", "blablu")


def test_branch_literal_shortcut():
    import re
    assert None == re.search("bl|a|c", "hello")


def test_literal_search():
    import re
    assert re.search(r"b(\d)", "ababbbab1")
    assert None == re.search(r"b(\d)", "ababbbab")


def test_repeat_one_literal_tail():
    import re
    assert re.search(".+ab", "wowowowawoabwowo")
    assert None == re.search(".+ab", "wowowaowowo")


def test_split_empty():
    import re
    assert re.split('', '') == ['', '']
    assert re.split('', 'ab') == ['', 'a', 'b', '']
    assert re.split('a*', '') == ['', '']
    assert re.split('a*', 'a') == ['', '', '']
    assert re.split('a*', 'aa') == ['', '', '']
    assert re.split('a*', 'baaac') == ['', 'b', '', 'c', '']


def test_type_names():
    import re
    assert repr(re.Pattern) == "<class 're.Pattern'>"
    assert repr(re.Match) == "<class 're.Match'>"


# ---------------------------------------------------------------------------
# AppTestUnicodeExtra
# ---------------------------------------------------------------------------

def test_string_attribute():
    import re
    match = re.search(u"\u1234", u"\u1233\u1234\u1235")
    assert match.string == u"\u1233\u1234\u1235"
    match = re.search(u"a", u"bac")
    assert match.string == u"bac"


def test_string_attribute_is_original_string():
    import re
    class mystr(type(u"")):
        pass
    s = mystr(u"\u1233\u1234\u1235")
    match = re.search(u"\u1234", s)
    assert match.string is s


def test_match_start():
    import re
    match = re.search(u"\u1234", u"\u1233\u1234\u1235")
    assert match.start() == 1


def test_match_repr_span():
    import re
    match = re.match(u"\u1234", u"\u1234")
    assert match.span() == (0, 1)
    assert "span=(0, 1), match='\u1234'" in repr(match)


def test_match_repr_truncation():
    import re
    s = "xy" + u"\u1234" * 50
    match = re.match(s, s)
    assert "span=(0, 52), match=" + repr(s)[:50] + ">" in repr(match)


def test_pattern_repr_truncation():
    import re
    s = "xy" + u"\u1234" * 200
    pattern = re.compile(s)
    assert repr(pattern) == "re.compile(%s)" % (repr(s)[:200],)


def test_subx_unusual_types_no_match():
    import re
    result = re.sub(b"x", lambda x: 1/0, memoryview(b"yz"))
    assert type(result) is bytes
    assert result == b"yz"
    class U(str): pass
    result = re.sub(u"x", lambda x: 1/0, U(u"yz"))
    assert type(result) is str
    assert result == u"yz"
    class B(bytes): pass
    result = re.sub(b"x", lambda x: 1/0, B(b"yz"))
    assert type(result) is bytes
    assert result == b"yz"


def test_bug_40736():
    import re
    with pytest.raises(TypeError) as exc_info:
        re.search("x*", 5)
    assert "got 'int'" in str(exc_info.value)
    with pytest.raises(TypeError) as exc_info:
        re.search("x*", None)
    assert "got 'NoneType'" in str(exc_info.value)


def test_search_releases_buffer():
    import re
    s = bytearray(b'abcdefgh')
    m = re.search(b'[a-h]+', s)
    m2 = re.search(b'[e-h]+', s)
    assert m.group() == b'abcdefgh'
    assert m2.group() == b'efgh'
    s[:] = b'xyz'
    assert m.group() == b'xyz'
    assert m2.group() == b''
