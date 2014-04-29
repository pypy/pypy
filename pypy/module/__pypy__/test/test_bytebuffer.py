class AppTest(object):
    spaceconfig = dict(usemodules=['__pypy__'])

    def test_bytebuffer(self):
        from __pypy__ import bytebuffer
        b = bytebuffer(12)
        assert len(b) == 12
        b[3] = b'!'
        b[5] = b'?'
        assert b[2:7] == b'\x00!\x00?\x00'
        b[9:] = b'+-*'
        assert b[-1] == b'*'
        assert b[-2] == b'-'
        assert b[-3] == b'+'
        exc = raises(TypeError, "b[3] = b'abc'")
        assert str(exc.value) == "right operand must be a single byte"
        exc = raises(TypeError, "b[3:5] = b'abc'")
        assert str(exc.value) == "right operand length must match slice length"
        exc = raises(TypeError, "b[3:7:2] = b'abc'")
        assert str(exc.value) == "right operand length must match slice length"

        b = bytebuffer(10)
        b[1:3] = b'xy'
        assert bytes(b) == b"\x00xy" + b"\x00" * 7
        b[4:8:2] = b'zw'
        assert bytes(b) == b"\x00xy\x00z\x00w" + b"\x00" * 3
        r = str(buffer(u'#'))
        b[6:6+len(r)] = u'#'
        assert str(b[:6+len(r)]) == "\x00xy\x00z\x00" + r
