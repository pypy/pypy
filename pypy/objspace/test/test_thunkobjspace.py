
class AppTest_Thunk:

    objspacename = 'thunk'

    def test_simple(self):
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
        x = 5
        y = 6
        assert x is not y
        become(x, y)
        assert x is y

    def test_id(self):
        # these are the Smalltalk semantics of become().
        x = 5; idx = id(x)
        y = 6; idy = id(y)
        assert idx != idy
        become(x, y)
        assert id(x) == id(y) == idy

    def test_double_become(self):
        x = 5
        y = 6
        z = 7
        become(x, y)
        become(y, z)
        assert x is y is z
