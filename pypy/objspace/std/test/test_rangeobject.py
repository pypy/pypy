import autopath, py

from pypy.conftest import gettestobjspace

class AppTestRangeListObject(object):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withrangelist": True})
        cls.w_not_forced = cls.space.appexec([], """():
            import sys
            def f(r):
                return (isinstance(r, list) and
                        "W_ListObject" not in sys.pypy_repr(r))
            return f
        """)

    def test_simple(self):
        result = []
        r = range(1, 8, 2)
        for i in r:
            result.append(i)
        assert result == [1, 3, 5, 7]
        assert self.not_forced(r)

    def test_getitem_slice(self):
        result = []
        r = range(1, 100, 2)
        for i in r[40:30:-2]:
            result.append(i)
        assert result == [81, 77, 73, 69, 65]
        assert self.not_forced(r)

    def test_repr(self):
        r = range(5)
        assert repr(r) == "[0, 1, 2, 3, 4]"
        assert self.not_forced(r)

    def test_force(self):
        r = range(10)
        r[0] = 42
        assert not self.not_forced(r)
        assert r == [42, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    def test_reverse(self):
        r = range(10)
        r.reverse()
        assert self.not_forced(r)
        assert r == range(9, -1, -1)

    def test_sort(self):
        r = range(10, -1, -1)
        r.sort()
        assert self.not_forced(r)
        assert r == range(11)
        r = range(11)
        r.sort(reverse=True)
        assert self.not_forced(r)
        assert r == range(10, -1, -1)
        r = range(100)
        r[0] = 999
        assert not self.not_forced(r)
        r.sort()
        assert r == range(1, 100) + [999]
