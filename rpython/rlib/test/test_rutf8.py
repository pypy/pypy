
from hypothesis import given, strategies, settings

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

def error_handler(errors, encoding, msg, char, start, end):
    raise UnicodeDecodeError(encoding, char, start, end, msg)

@given(strategies.binary())
def test_str_check_utf8(s):
    try:
        u = s.decode("utf8")
        valid = True
    except UnicodeDecodeError as e:
        valid = False
    try:
        consumed, length = rutf8.str_check_utf8(s, len(s), None,
            errorhandler=error_handler, final=True)
    except UnicodeDecodeError as a:
        assert not valid
        assert a.start == e.start
        # assert a.end == e.end, ideally
    else:
        assert valid
        assert consumed == len(s)
        assert length == len(u)

@given(strategies.binary())
def test_str_decode_raw_utf8_escape(uni):
    return # XXX fix details
    rutf8.str_decode_raw_utf8_escape(uni, len(uni), None)