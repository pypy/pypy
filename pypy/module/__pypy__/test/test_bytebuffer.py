class AppTest(object):
    spaceconfig = dict(usemodules=['__pypy__'])

    def test_bytebuffer(self):
        from __pypy__ import bytebuffer
        b = bytebuffer(12)
        assert isinstance(b, buffer)
        assert len(b) == 12
        b[3] = '!'
        b[5] = '?'
        assert b[2:7] == '\x00!\x00?\x00'
        b[9:] = '+-*'
        assert b[-1] == '*'
        assert b[-2] == '-'
        assert b[-3] == '+'
        exc = raises(TypeError, "b[3] = 'abc'")
        assert str(exc.value) == "right operand must be a single byte"
        exc = raises(TypeError, "b[3:5] = 'abc'")
        assert str(exc.value) == "right operand length must match slice length"
        exc = raises(TypeError, "b[3:7:2] = 'abc'")
        assert str(exc.value) == "right operand length must match slice length"

        b = bytebuffer(10)
        b[1:3] = 'xy'
        assert str(b) == "\x00xy" + "\x00" * 7
        b[4:8:2] = 'zw'
        assert str(b) == "\x00xy\x00z\x00w" + "\x00" * 3
        r = str(buffer(u'#'))
        b[6:6+len(r)] = u'#'
        assert str(b[:6+len(r)]) == "\x00xy\x00z\x00" + r
