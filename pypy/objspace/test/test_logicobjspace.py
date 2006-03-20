from pypy.conftest import gettestobjspace

class AppTest_Logic(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_simple(self):
        X = newvar()
        assert is_free(X)
        bind(X, 1)
        assert type(X) == int
        assert is_bound(X)
        assert is_bound(1)
        raises(TypeError, bind, 1, 2)

    def test_setitem(self):
        x = newvar()
        d = {5: x}
        d[6] = x
        d[7] = []
        d[7].append(x)
        y = d[5], d[6], d.values(), d.items()
        for x in [d[5], d[6], d[7][0]]:
            assert is_free(d[5])
        bind(x, 1)
        for x in [d[5], d[6], d[7][0]]:
            assert is_bound(d[5])

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

    def test_use_unbound_var(self):
        X = newvar()
        def f(x):
            return x + 1
        raises(RuntimeError, f, X)

    def test_bind_to_self(self):
        X = newvar()
        bind(X, X)
        bind(X, 1)
        assert X == 1

    def test_eq_unifies_simple(self):
        X = newvar()
        Y = newvar()
        assert X == Y
        assert X == 1
        assert is_bound(Y)
        assert Y == 1

    def test_ne_of_unified_vars(self):
        X = newvar()
        Y = newvar()
        assert X == Y
        assert not X != Y

    def test_cmp(self):
        X = newvar()
        Y = newvar()
        assert cmp(X, Y) == 0
        assert is_free(X)
        assert is_free(Y)
        assert X == 1
        assert is_bound(Y)
        assert Y == 1

    def test_is(self):
        X = newvar()
        x = 1
        assert X is x
        assert X == 1
        assert X is x

