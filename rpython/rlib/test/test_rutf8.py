
from hypothesis import given, strategies, settings

from rpython.rlib import rutf8, runicode

@given(strategies.integers(min_value=0, max_value=runicode.MAXUNICODE))
def test_unichr_as_utf8(i):
    assert rutf8.unichr_as_utf8(i) == runicode.UNICHR(i).encode('utf8')

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
def test_str_decode_raw_utf8_escape(uni):
    return # XXX fix details
    rutf8.str_decode_raw_utf8_escape(uni, len(uni), None)