
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
        def f():
            computed.append(True)
            return 6*7
        x = thunk(f)
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
