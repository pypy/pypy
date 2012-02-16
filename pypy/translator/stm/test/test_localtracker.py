from pypy.translator.stm.localtracker import StmLocalTracker
from pypy.translator.translator import TranslationContext, graphof
from pypy.conftest import option
from pypy.rlib.jit import hint
from pypy.rlib.nonconst import NonConstant
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel


class TestStmLocalTracker(object):

    def translate(self, func, sig):
        t = TranslationContext()
        self.translator = t
        t._seen_locals = {}
        t.buildannotator().build_types(func, sig)
        t.buildrtyper().specialize()
        if option.view:
            t.view()
        localtracker = StmLocalTracker(t)
        self.localtracker = localtracker
        return localtracker

    def check(self, expected_names):
        got_local_names = set()
        for name, v in self.translator._seen_locals.items():
            if self.localtracker.is_local(v):
                got_local_names.add(name)
        assert got_local_names == set(expected_names)


    def test_no_local(self):
        x = X(42)
        def g(x):
            return x.n
        def f(n):
            return g(x)
        #
        localtracker = self.translate(f, [int])
        self.check([])

    def test_freshly_allocated(self):
        z = [lltype.malloc(S), lltype.malloc(S)]
        def f(n):
            x = lltype.malloc(S)
            x.n = n
            y = lltype.malloc(S)
            y.n = n+1
            _see(x, 'x')
            _see(y, 'y')
            _see(z[n % 2], 'z')
            return x.n, y.n
        #
        self.translate(f, [int])
        self.check(['x', 'y'])      # x and y are locals; z is prebuilt

    def test_freshly_allocated_in_one_path(self):
        z = lltype.malloc(S)
        def f(n):
            x = lltype.malloc(S)
            x.n = n
            if n > 5:
                y = lltype.malloc(S)
                y.n = n+1
            else:
                y = z
            _see(x, 'x')
            _see(y, 'y')
            return x.n + y.n
        #
        self.translate(f, [int])
        self.check(['x'])      # x is local; y not, as it can be equal to z

    def test_freshly_allocated_in_the_other_path(self):
        z = lltype.malloc(S)
        def f(n):
            x = lltype.malloc(S)
            x.n = n
            if n > 5:
                y = z
            else:
                y = lltype.malloc(S)
                y.n = n+1
            _see(x, 'x')
            _see(y, 'y')
            return x.n + y.n
        #
        self.translate(f, [int])
        self.check(['x'])      # x is local; y not, as it can be equal to z

    def test_freshly_allocated_in_loop(self):
        z = lltype.malloc(S)
        def f(n):
            while True:
                x = lltype.malloc(S)
                x.n = n
                n -= 1
                if n < 0:
                    break
            _see(x, 'x')
            return x.n
        #
        self.translate(f, [int])
        self.check(['x'])      # x is local

    def test_none_variable_is_local(self):
        def f(n):
            if n > 5:
                x = lltype.nullptr(S)
            else:
                x = lltype.malloc(S)
                x.n = n
            _see(x, 'x')
        #
        localtracker = self.translate(f, [int])
        self.check(['x'])

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

    def test_instantiate_returns_fresh_object(self):
        def f(n):
            if n > 5:
                cls = X
            else:
                cls = Y
            _see(cls(n), 'x')
        #
        self.translate(f, [int])
        self.check(['x'])


S = lltype.GcStruct('S', ('n', lltype.Signed))

class X:
    def __init__(self, n):
        self.n = n

class Y(X):
    pass


def _see(var, name):
    pass

class Entry(ExtRegistryEntry):
    _about_ = _see

    def compute_result_annotation(self, s_var, s_name):
        return annmodel.s_None

    def specialize_call(self, hop):
        v = hop.inputarg(hop.args_r[0], arg=0)
        name = hop.args_s[1].const
        assert name not in hop.rtyper.annotator.translator._seen_locals, (
            "duplicate name %r" % (name,))
        hop.rtyper.annotator.translator._seen_locals[name] = v
        return hop.inputconst(lltype.Void, None)
