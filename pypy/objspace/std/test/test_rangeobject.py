import autopath, py

from pypy.conftest import gettestobjspace

class AppTestRangeListObject(object):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withrangelist": True})

    def test_simple(self):
        result = []
        for i in range(1, 8, 2):
            result.append(i)
        assert result == [1, 3, 5, 7]

    def test_getitem_slice(self):
        result = []
        for i in range(1, 100, 2)[40:30:-2]:
            result.append(i)
        assert result == [81, 77, 73, 69, 65]

    def test_repr(self):
        assert repr(range(5)) == "[0, 1, 2, 3, 4]"

    def test_force(self):
        r = range(10)
        r[0] = 42
        assert r == [42, 1, 2, 3, 4, 5, 6, 7, 8, 9]
