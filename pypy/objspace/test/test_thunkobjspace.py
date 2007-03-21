from pypy.conftest import gettestobjspace

class AppTest_Thunk:

    def setup_class(cls):
        cls.space = gettestobjspace('thunk')

    def test_simple(self):
        from __pypy__ import thunk, become
        computed = []
        def f():
            computed.append(True)
            return 6*7
        x = thunk(f)
        assert computed == []
        t = type(x)
        assert t is int
        assert computed == [True]
        t = type(x)
        assert t is int
        assert computed == [True]

    def test_setitem(self):
        from __pypy__ import thunk, become
        computed = []
        def f(a):
            computed.append(True)
            return a*7
        x = thunk(f, 6)
        d = {5: x}
        d[6] = x
        d[7] = []
        d[7].append(x)
        assert computed == []
        y = d[5], d[6], d.values(), d.items()
        assert computed == []
        d[7][0] += 1
        assert computed == [True]
        assert d[7] == [43]

    def test_become(self):
        from __pypy__ import thunk, become
        x = []
        y = []
        assert x is not y
        become(x, y)
        assert x is y

    def test_id(self):
        from __pypy__ import thunk, become
        # these are the Smalltalk semantics of become().
        x = []; idx = id(x)
        y = []; idy = id(y)
        assert idx != idy
        become(x, y)
        assert id(x) == id(y) == idy

    def test_double_become(self):
        from __pypy__ import thunk, become
        x = []
        y = []
        z = []
        become(x, y)
        become(y, z)
        assert x is y is z

    def test_thunk_forcing_while_forcing(self):
        from __pypy__ import thunk, become
        def f():
            return x+1
        x = thunk(f)
        raises(RuntimeError, 'x+1')

    def INPROGRESS_test_thunk_forcing_while_forcing_2(self):
        from __pypy__ import thunk, become
        def f():
            return x
        x = thunk(f)
        raises(RuntimeError, 'x+1')

    def test_is_thunk(self):
        from __pypy__ import thunk, become, is_thunk
        def f():
            pass
        assert is_thunk(thunk(f))
        assert not is_thunk(42)

    def test_lazy(self):
        from __pypy__ import lazy
        lst = []
        def f(x):
            lst.append(x)
            return x+5
        f = lazy(f)
        y = f(3)
        assert lst == []
        assert type(y) is int
        assert lst == [3]
        assert type(y) is int
        assert lst == [3]
