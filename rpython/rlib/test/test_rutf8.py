import py
import sys
from hypothesis import given, strategies, settings, example

from rpython.rlib import rutf8, runicode


@given(strategies.characters(), strategies.booleans())
def test_unichr_as_utf8(c, allow_surrogates):
    i = ord(c)
    if not allow_surrogates and 0xD800 <= i <= 0xDFFF:
        py.test.raises(ValueError, rutf8.unichr_as_utf8, i, allow_surrogates)
    else:
        u = rutf8.unichr_as_utf8(i, allow_surrogates)
        assert u == c.encode('utf8')

@given(strategies.binary())
def test_check_ascii(s):
    raised = False
    try:
        s.decode('ascii')
    except UnicodeDecodeError as e:
        raised = True
    try:
        rutf8.check_ascii(s)
    except rutf8.CheckError:
        assert raised
    else:
        assert not raised

@given(strategies.binary(), strategies.booleans())
def test_check_utf8(s, allow_surrogates):
    _test_check_utf8(s, allow_surrogates)

@given(strategies.text(), strategies.booleans())
def test_check_utf8_valid(u, allow_surrogates):
    _test_check_utf8(u.encode('utf-8'), allow_surrogates)

def _test_check_utf8(s, allow_surrogates):
    try:
        u, _ = runicode.str_decode_utf_8(s, len(s), None, final=True,
                                         allow_surrogates=allow_surrogates)
        valid = True
    except UnicodeDecodeError as e:
        valid = False
    try:
        length = rutf8.check_utf8(s, allow_surrogates)
    except rutf8.CheckError:
        assert not valid
    else:
        assert valid
        assert length == len(u)

@given(strategies.characters())
def test_next_pos(uni):
    skips = []
    for elem in uni:
        skips.append(len(elem.encode('utf8')))
    pos = 0
    i = 0
    utf8 = uni.encode('utf8')
    while pos < len(utf8):
        new_pos = rutf8.next_codepoint_pos(utf8, pos)
        assert new_pos - pos == skips[i]
        i += 1
        pos = new_pos

def test_check_newline_utf8():
    for i in xrange(sys.maxunicode):
        if runicode.unicodedb.islinebreak(i):
            assert rutf8.islinebreak(unichr(i).encode('utf8'), 0)
        else:
            assert not rutf8.islinebreak(unichr(i).encode('utf8'), 0)

def test_isspace_utf8():
    for i in xrange(sys.maxunicode):
        if runicode.unicodedb.isspace(i):
            assert rutf8.isspace(unichr(i).encode('utf8'), 0)
        else:
            assert not rutf8.isspace(unichr(i).encode('utf8'), 0)

@given(strategies.characters(), strategies.text())
def test_utf8_in_chars(ch, txt):
    response = rutf8.utf8_in_chars(ch.encode('utf8'), 0, txt.encode('utf8'))
    r = (ch in txt)
    assert r == response
