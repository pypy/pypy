
import sys
from hypothesis import given, strategies, settings, example

from rpython.rlib import rutf8, runicode

@given(strategies.integers(min_value=0, max_value=runicode.MAXUNICODE))
def test_unichr_as_utf8(i):
    u, lgt = rutf8.unichr_as_utf8(i)
    r = runicode.UNICHR(i)
    assert u == r.encode('utf8')

@given(strategies.binary())
def test_check_ascii(s):
    raised = False
    try:
        s.decode('ascii')
    except UnicodeDecodeError as e:
        raised = True
    try:
        rutf8.check_ascii(s)
    except rutf8.AsciiCheckError as a:
        assert raised
        assert a.pos == e.start
    else:
        assert not raised

@given(strategies.binary())
def test_str_check_utf8(s):
    try:
        u, _ = runicode.str_decode_utf_8(s, len(s), None, final=True)
        valid = True
    except UnicodeDecodeError as e:
        valid = False
    try:
        consumed, length = rutf8.str_check_utf8(s, len(s), final=True)
    except rutf8.Utf8CheckError as a:
        assert not valid
        assert a.startpos == e.start
        # assert a.end == e.end, ideally
    else:
        assert valid
        assert consumed == len(s)
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
