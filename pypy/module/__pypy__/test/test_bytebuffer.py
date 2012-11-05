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
