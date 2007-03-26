import py

from pypy.conftest import gettestobjspace, option

class AppTestRangeListObject(object):

    def setup_class(cls):
        if option.runappdirect:
            py.test.skip("__pypy__.internal_repr() cannot be used to see "
                         "if a range list was forced on top of pypy-c")
        cls.space = gettestobjspace(**{"objspace.std.withrangelist": True})
        cls.w_not_forced = cls.space.appexec([], """():
            import __pypy__
            def f(r):
                return (isinstance(r, list) and
                        "W_ListObject" not in __pypy__.internal_repr(r))
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
        r = range(3)
        r[0] = 1
        assert r == [1, 1, 2]
        r.reverse()
        assert r == [2, 1, 1]

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

    def test_pop(self):
        r = range(10)
        res = r.pop()
        assert res == 9
        assert self.not_forced(r)
        assert repr(r) == repr(range(9))
        res = r.pop(0)
        assert res == 0
        assert self.not_forced(r)
        assert repr(r) == repr(range(1, 9))
        res = r.pop(len(r) - 1)
        assert res == 8
        assert self.not_forced(r)
        assert repr(r) == repr(range(1, 8))
        res = r.pop(2)
        assert res == 3
        assert not self.not_forced(r)
        assert r == [1, 2, 4, 5, 6, 7]
        res = r.pop(2)
        assert res == 4
        assert not self.not_forced(r)
        assert r == [1, 2, 5, 6, 7]
       
