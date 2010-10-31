from pypy.objspace.std.test import test_longobject
from pypy.conftest import gettestobjspace


class AppTestSmallLong(test_longobject.AppTestLong):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withsmalllong": True})

    def test_sl_simple(self):
        import __pypy__
        s = __pypy__.internal_repr(5L)
        assert 'SmallLong' in s
