import py
from pypy.conftest import gettestobjspace


class AppTestLocal(object):
    def test_local(self):
        import __pypy__
        x = __pypy__.local()
        x.foo = 42
        assert x.foo == 42     # hard to test more :-)


class AppTestLocalWithThreads(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['thread'])

    def test_local(self):
        import __pypy__, thread
        assert __pypy__.local is thread._local
