from pypy.conftest import gettestobjspace

class AppTest_Logic(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_simple(self):
        X = newvar()
        assert is_unbound(X)
        bind(X, 1)
        assert type(X) == int
        assert not is_unbound(X)
        assert not is_unbound(1)
        raises(TypeError, bind, 1, 2)

    def test_setitem(self):
        x = newvar()
        d = {5: x}
        d[6] = x
        d[7] = []
        d[7].append(x)
        y = d[5], d[6], d.values(), d.items()
        for x in [d[5], d[6], d[7][0]]:
            assert is_unbound(d[5])
        bind(x, 1)
        for x in [d[5], d[6], d[7][0]]:
            assert not is_unbound(d[5])

    def test_unbound_unification_simple(self):
        X = newvar()
        Y = newvar()
        bind(X, Y)
        bind(X, 1)
        assert X == 1
        assert Y == 1

    def test_unbound_unification_long(self):
        l = [newvar() for i in range(40)]
        for i in range(39):
            bind(l[i], l[i + 1])
        bind(l[20], 1)
        for i in range(40):
            assert l[i] == 1

