import _codecs

def test_lone_low_surrogate_utf16():
    data = '\udc02'.encode('utf-16', 'surrogatepass')
    decode = _codecs.utf_16_ex_decode
    (result, consumed, bo) = decode(data, 'surrogatepass', False)
    assert result == '\uDC02'

def test_lone_low_surrogate_utf16le():
    data = '\udc02'.encode('utf-16-le', 'surrogatepass')
    decode = _codecs.utf_16_le_decode
    (result, consumed) = decode(data, 'surrogatepass', False)
    assert result == '\uDC02'

def test_surrogateescape_slowness():
    # should not take ages, basically
    l = len(('a\udcdb'*500).encode('utf8', 'surrogateescape'))
    assert l == 1000

def test_utf8_many_surrogates_in_a_row():
    import _codecs
    def h(exc):
        assert exc.start == 0
        assert exc.end == 10
        return '', exc.end
    _codecs.register_error("test.test_utf8_many_surrogates_in_a_row", h)
    res = ('\udcdb'*10 + 'abc').encode("utf8", "test.test_utf8_many_surrogates_in_a_row")
    assert res == b'abc'
