import py
import os

from pypy.translator.translator import TranslationContext
from pypy.translator.c import genc
from pypy.rpython.lltypesystem import lltype
from pypy import conftest


class TestRefcount(object):
    def compile_func(self, fn, inputtypes, t=None):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.gc = "ref"
        config.translation.countmallocs = True
        if t is None:
            t = TranslationContext(config=config)
        if inputtypes is not None:
            t.buildannotator().build_types(fn, inputtypes)
            t.buildrtyper().specialize()
        builder = genc.CExtModuleBuilder(t, fn, config=config)
        builder.generate_source()
        builder.compile()
        if conftest.option.view:
            t.view()
        compiled_fn = builder.get_entry_point()
        malloc_counters = builder.get_malloc_counters()
        def checking_fn(*args, **kwds):
            try:
                return compiled_fn(*args, **kwds)
            finally:
                mallocs, frees = malloc_counters()
                assert mallocs == frees
        return checking_fn

    def test_something(self):
        def f():
            return 1
        fn = self.compile_func(f, [])
        assert fn() == 1

    def test_something_more(self):
        S = lltype.GcStruct("S", ('x', lltype.Signed))
        def f(x):
            s = lltype.malloc(S)
            s.x = x
            return s.x
        fn = self.compile_func(f, [int])
        assert fn(1) == 1

    def test_call_function(self):
        class C:
            pass
        def f():
            c = C()
            c.x = 1
            return c
        def g():
            return f().x
        fn = self.compile_func(g, [])
        assert fn() == 1

    def test_multiple_exits(self):
        S = lltype.GcStruct("S", ('x', lltype.Signed))
        T = lltype.GcStruct("T", ('y', lltype.Signed))
        def f(n):
            c = lltype.malloc(S)
            d = lltype.malloc(T)
            d.y = 1
            e = lltype.malloc(T)
            e.y = 2
            if n:
                x = d
            else:
                x = e
            return x.y
        fn = self.compile_func(f, [int])
        assert fn(1) == 1
        assert fn(0) == 2


    def test_cleanup_vars_on_call(self):
        S = lltype.GcStruct("S", ('x', lltype.Signed))
        def f():
            return lltype.malloc(S)
        def g():
            s1 = f()
            s1.x = 42
            s2 = f()
            s3 = f()
            return s1.x
        fn = self.compile_func(g, [])
        assert fn() == 42

    def test_multiply_passed_var(self):
        S = lltype.GcStruct("S", ('x', lltype.Signed))
        def f(x):
            if x:
                a = lltype.malloc(S)
                a.x = 1
                b = a
            else:
                a = lltype.malloc(S)
                a.x = 1
                b = lltype.malloc(S)
                b.x = 2
            return a.x + b.x
        fn = self.compile_func(f, [int])
        fn(1) == 2
        fn(0) == 3

    def test_write_barrier(self):
        S = lltype.GcStruct("S", ('x', lltype.Signed))
        T = lltype.GcStruct("T", ('s', lltype.Ptr(S)))
        def f(x):
            s = lltype.malloc(S)
            s.x = 0
            s1 = lltype.malloc(S)
            s1.x = 1
            s2 = lltype.malloc(S)
            s2.x = 2
            t = lltype.malloc(T)
            t.s = s
            if x:
                t.s = s1
            else:
                t.s = s2
            return t.s.x + s.x + s1.x + s2.x
        fn = self.compile_func(f, [int])
        assert fn(1) == 4
        assert fn(0) == 5

    def test_del_basic(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed), rtti=True)
        TRASH = lltype.GcStruct('TRASH', ('x', lltype.Signed))
        GLOBAL = lltype.Struct('GLOBAL', ('x', lltype.Signed))
        glob = lltype.malloc(GLOBAL, immortal=True)
        def destructor(s):
            glob.x = s.x + 1
        def type_info_S(s):
            return lltype.getRuntimeTypeInfo(S)

        def g(n):
            s = lltype.malloc(S)
            s.x = n
            # now 's' should go away
        def entrypoint(n):
            g(n)
            # llop.gc__collect(lltype.Void)
            return glob.x

        t = TranslationContext()
        t.buildannotator().build_types(entrypoint, [int])
        rtyper = t.buildrtyper()
        destrptr = rtyper.annotate_helper_fn(destructor, [lltype.Ptr(S)])
        rtyper.attachRuntimeTypeInfoFunc(S, type_info_S, destrptr=destrptr)
        rtyper.specialize()
        fn = self.compile_func(entrypoint, None, t)

        res = fn(123)
        assert res == 124

    def test_del_catches(self):
        import os
        def g():
            pass
        class A(object):
            def __del__(self):
                try:
                    g()
                except:
                    os.write(1, "hallo")
        def f1(i):
            if i:
                raise TypeError
        def f(i):
            a = A()
            f1(i)
            a.b = 1
            return a.b
        fn = self.compile_func(f, [int])
        assert fn(0) == 1
        assert py.test.raises(TypeError, fn, 1)

    def test_del_raises(self):
        class B(object):
            def __del__(self):
                raise TypeError
        def func():
            b = B()
        fn = self.compile_func(func, [])
        # does not crash
        fn()

    def test_wrong_order_setitem(self):
        import os
        class A(object):
            pass
        a = A()
        a.b = None
        class B(object):
            def __del__(self):
                a.freed += 1
                a.b = None
        def f(n):
            a.freed = 0
            a.b = B()
            if n:
                a.b = None
            return a.freed
        fn = self.compile_func(f, [int])
        res = fn(1)
        assert res == 1

    def test_wrong_startblock_incref(self):
        class B(object):
            pass
        def g(b):
            while True:
                b.x -= 10
                if b.x < 0:
                    return b.x
        def f(n):
            b = B()
            b.x = n
            return g(b)

        # XXX obscure: remove the first empty block in the graph of 'g'
        t = TranslationContext()
        graph = t.buildflowgraph(g)
        assert graph.startblock.operations == []
        graph.startblock = graph.startblock.exits[0].target
        from pypy.objspace.flow.model import checkgraph
        checkgraph(graph)
        t._prebuilt_graphs[g] = graph

        fn = self.compile_func(f, [int], t)
        res = fn(112)
        assert res == -8
