from pypy.translator.stm.localtracker import StmLocalTracker
from pypy.translator.translator import TranslationContext, graphof
from pypy.conftest import option
from pypy.rlib.jit import hint


class TestStmLocalTracker(object):

    def translate(self, func, sig):
        t = TranslationContext()
        t.buildannotator().build_types(func, sig)
        t.buildrtyper().specialize()
        if option.view:
            t.view()
        localtracker = StmLocalTracker(t)
        self.localtracker = localtracker
        localtracker.track_and_propagate_locals()
        return localtracker


    def test_no_local(self):
        x = X(42)
        def g(x):
            return x.n
        def f(n):
            return g(x)
        #
        localtracker = self.translate(f, [int])
        assert not localtracker.locals

    def test_freshly_allocated(self):
        z = [42]
        def f(n):
            x = [n]
            y = [n+1]
            _see(x, 'x')
            _see(y, 'y')
            _see(z, 'z')
            return x[0], y[0]
        #
        self.translate(f, [int])
        self.check(['x', 'y'])      # x and y are locals; z is prebuilt

    def test_freshly_allocated_to_g(self):
        def g(x):
            _see(x, 'x')
            return x[0]
        def f(n):
            g([n])
            g([n+1])
            g([n+2])
        #
        self.translate(f, [int])
        self.check(['x'])           # x is a local in all possible calls to g()

    def test_not_always_freshly_allocated_to_g(self):
        z = [42]
        def g(x):
            _see(x, 'x')
            return x[0]
        def f(n):
            y = [n]
            g(y)
            g(z)
            _see(y, 'y')
        #
        self.translate(f, [int])
        self.check(['y'])    # x is not a local in one possible call to g()
                             # but y is still a local

    def test_constructor_allocates_freshly(self):
        def f(n):
            x = X(n)
            _see(x, 'x')
        #
        self.translate(f, [int])
        self.check(['x'])

    def test_fresh_in_init(self):
        class Foo:
            def __init__(self, n):
                self.n = n
                _see(self, 'foo')
        def f(n):
            return Foo(n)
        #
        self.translate(f, [int])
        self.check(['foo'])

    def test_returns_fresh_object(self):
        def g(n):
            return X(n)
        def f(n):
            x = g(n)
            _see(x, 'x')
        #
        self.translate(f, [int])
        self.check(['x'])

    def test_indirect_call_returns_fresh_object(self):
        def g(n):
            return X(n)
        def h(n):
            return Y(n)
        lst = [g, h]
        def f(n):
            x = lst[n % 2](n)
            _see(x, 'x')
        #
        self.translate(f, [int])
        self.check(['x'])

    def test_indirect_call_may_return_nonfresh_object(self):
        z = X(42)
        def g(n):
            return X(n)
        def h(n):
            return z
        lst = [g, h]
        def f(n):
            x = lst[n % 2](n)
            _see(x, 'x')
        #
        self.translate(f, [int])
        self.check([])


class X:
    def __init__(self, n):
        self.n = n

class Y(X):
    pass
