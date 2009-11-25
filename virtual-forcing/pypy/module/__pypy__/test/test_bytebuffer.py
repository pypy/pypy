import py
from pypy.conftest import gettestobjspace

class AppTest(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['__pypy__'])

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
