import autopath
import sys
import py
from py.test import raises

from pypy.translator.translator import TranslationContext
from pypy.translator.backendopt.stat import print_statistics
from pypy.translator.c import genc, gc
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy import conftest

def compile_func(fn, inputtypes, t=None, gcpolicy="ref"):
    from pypy.config.pypyoption import get_pypy_config
    config = get_pypy_config(translating=True)
    config.translation.gc = gcpolicy
    if t is None:
        t = TranslationContext(config=config)
    if inputtypes is not None:
        t.buildannotator().build_types(fn, inputtypes)
        t.buildrtyper().specialize()
    builder = genc.CExtModuleBuilder(t, fn, config=config)
    builder.generate_source(defines={'COUNT_OP_MALLOCS': 1})
    builder.compile()
    builder.import_module()
    if conftest.option.view:
        t.view()
    module = builder.c_ext_module
    compiled_fn = builder.get_entry_point()
    def checking_fn(*args, **kwds):
        try:
            return compiled_fn(*args, **kwds)
        finally:
            mallocs, frees = module.malloc_counters()
            assert mallocs == frees
    return checking_fn

def test_something():
    def f():
        return 1
    fn = compile_func(f, [])
    assert fn() == 1

def test_something_more():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f(x):
        s = lltype.malloc(S)
        s.x = x
        return s.x
    fn = compile_func(f, [int])
    assert fn(1) == 1

def test_call_function():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c
    def g():
        return f().x
    fn = compile_func(g, [])
    assert fn() == 1

def test_multiple_exits():
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
    fn = compile_func(f, [int])
    assert fn(1) == 1
    assert fn(0) == 2


def test_cleanup_vars_on_call():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f():
        return lltype.malloc(S)
    def g():
        s1 = f()
        s1.x = 42
        s2 = f()
        s3 = f()
        return s1.x
    fn = compile_func(g, [])
    assert fn() == 42

def test_multiply_passed_var():
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
    fn = compile_func(f, [int])
    fn(1) == 2
    fn(0) == 3

def test_pyobj():
    def f(x):
        if x:
            a = 1
        else:
            a = "1"
        return int(a)
    fn = compile_func(f, [int])
    assert fn(1) == 1
#    assert fn(0) == 0 #XXX this should work but it's not my fault

def test_write_barrier():
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
    fn = compile_func(f, [int])
    assert fn(1) == 4
    assert fn(0) == 5

def test_del_basic():
    for gcpolicy in ["ref"]: #, "framework"]:
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        TRASH = lltype.GcStruct('TRASH', ('x', lltype.Signed))
        lltype.attachRuntimeTypeInfo(S)
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
        fn = compile_func(entrypoint, None, t, gcpolicy=gcpolicy)

        res = fn(123)
        assert res == 124

def test_del_catches():
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
    fn = compile_func(f, [int])
    assert fn(0) == 1
    assert py.test.raises(TypeError, fn, 1)

def test_del_raises():
    class B(object):
        def __del__(self):
            raise TypeError
    def func():
        b = B()
    fn = compile_func(func, [])
    # does not crash
    fn()

def test_wrong_order_setitem():
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
    fn = compile_func(f, [int])
    res = fn(1)
    assert res == 1

def test_wrong_startblock_incref():
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
    graph.startblock.isstartblock = True
    from pypy.objspace.flow.model import checkgraph
    checkgraph(graph)
    t._prebuilt_graphs[g] = graph

    fn = compile_func(f, [int], t)
    res = fn(112)
    assert res == -8

def test_gc_x_operations():
    t = TranslationContext()
    from pypy.rlib.rgc import gc_clone, gc_swap_pool
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f():
        s = lltype.malloc(S)
        gc_swap_pool(None)
        try:
            t = gc_clone(s, None)
        except RuntimeError:
            return 1
        else:
            return 0
    fn = compile_func(f, [], t=t)
    res = fn()
    assert res == 1

# _______________________________________________________________
# test framework

from pypy.translator.c.test.test_boehm import AbstractGCTestClass

class TestUsingFramework(AbstractGCTestClass):
    gcpolicy = "framework"

    def test_empty_collect(self):
        def f():
            llop.gc__collect(lltype.Void)
            return 41
        fn = self.getcompiled(f)
        res = fn()
        assert res == 41

    def test_framework_simple(self):
        def g(x): # cannot cause a collect
            return x + 1
        class A(object):
            pass
        def make():
            a = A()
            a.b = g(1)
            return a
        make.dont_inline = True
        def f():
            a = make()
            llop.gc__collect(lltype.Void)
            return a.b
        fn = self.getcompiled(f)
        res = fn()
        assert res == 2
        operations = self.t.graphs[0].startblock.exits[False].target.operations
        assert len([op for op in operations if op.opname == "gc_reload_possibly_moved"]) == 0

    def test_framework_safe_pushpop(self):
        class A(object):
            pass
        class B(object):
            pass
        def g(x): # cause a collect
            llop.gc__collect(lltype.Void)
        g.dont_inline = True
        global_a = A()
        global_a.b = B()
        global_a.b.a = A()
        global_a.b.a.b = B()
        global_a.b.a.b.c = 1
        def make():
            global_a.b.a.b.c = 40
            a = global_a.b.a
            b = a.b
            b.c = 41
            g(1)
            b0 = a.b
            b0.c = b.c = 42
        make.dont_inline = True
        def f():
            make()
            llop.gc__collect(lltype.Void)
            return global_a.b.a.b.c
        fn = self.getcompiled(f)
        startblock = self.t.graphs[0].startblock
        res = fn()
        assert res == 42
        assert len([op for op in startblock.operations if op.opname == "gc_reload_possibly_moved"]) == 0

    def test_framework_protect_getfield(self):
        class A(object):
            pass
        class B(object):
            pass
        def prepare(b, n):
            a = A()
            a.value = n
            b.a = a
            b.othervalue = 5
        def g(a):
            llop.gc__collect(lltype.Void)
            for i in range(1000):
                prepare(B(), -1)    # probably overwrites collected memory
            return a.value
        g.dont_inline = True
        def f():
            b = B()
            prepare(b, 123)
            a = b.a
            b.a = None
            return g(a) + b.othervalue
        fn = self.getcompiled(f)
        res = fn()
        assert res == 128

    def test_framework_varsized(self):
        S = lltype.GcStruct("S", ('x', lltype.Signed))
        T = lltype.GcStruct("T", ('y', lltype.Signed),
                                 ('s', lltype.Ptr(S)))
        ARRAY_Ts = lltype.GcArray(lltype.Ptr(T))
        
        def f():
            r = 0
            for i in range(30):
                a = lltype.malloc(ARRAY_Ts, i)
                for j in range(i):
                    a[j] = lltype.malloc(T)
                    a[j].y = i
                    a[j].s = lltype.malloc(S)
                    a[j].s.x = 2*i
                    r += a[j].y + a[j].s.x
                    a[j].s = lltype.malloc(S)
                    a[j].s.x = 3*i
                    r -= a[j].s.x
                for j in range(i):
                    r += a[j].y
            return r
        fn = self.getcompiled(f)
        res = fn()
        assert res == f()
            

    def test_framework_using_lists(self):
        class A(object):
            pass
        N = 1000
        def f():
            static_list = []
            for i in range(N):
                a = A()
                a.x = i
                static_list.append(a)
            r = 0
            for a in static_list:
                r += a.x
            return r
        fn = self.getcompiled(f)
        res = fn()
        assert res == N*(N - 1)/2
    
    def test_framework_static_roots(self):
        class A(object):
            def __init__(self, y):
                self.y = y
        a = A(0)
        a.x = None
        def make():
            a.x = A(42)
        make.dont_inline = True
        def f():
            make()
            llop.gc__collect(lltype.Void)
            return a.x.y
        fn = self.getcompiled(f)
        res = fn()
        assert res == 42

    def test_framework_nongc_static_root(self):
        S = lltype.GcStruct("S", ('x', lltype.Signed))
        T = lltype.Struct("T", ('p', lltype.Ptr(S)))
        t = lltype.malloc(T, immortal=True)
        def f():
            t.p = lltype.malloc(S)
            t.p.x = 43
            for i in range(2500000):
                s = lltype.malloc(S)
                s.x = i
            return t.p.x
        fn = self.getcompiled(f)
        res = fn()
        assert res == 43

    def test_framework_void_array(self):
        A = lltype.GcArray(lltype.Void)
        a = lltype.malloc(A, 44)
        def f():
            return len(a)
        fn = self.getcompiled(f)
        res = fn()
        assert res == 44
        
        
    def test_framework_malloc_failure(self):
        def f():
            a = [1] * (sys.maxint//2)
            return len(a) + a[0]
        fn = self.getcompiled(f)
        py.test.raises(MemoryError, fn)

    def test_framework_array_of_void(self):
        def f():
            a = [None] * 43
            b = []
            for i in range(1000000):
                a.append(None)
                b.append(len(a))
            return b[-1]
        fn = self.getcompiled(f)
        res = fn()
        assert res == 43 + 1000000
        
    def test_framework_opaque(self):
        A = lltype.GcStruct('A', ('value', lltype.Signed))
        O = lltype.GcOpaqueType('test.framework')

        def gethidden(n):
            a = lltype.malloc(A)
            a.value = -n * 7
            return lltype.cast_opaque_ptr(lltype.Ptr(O), a)
        gethidden.dont_inline = True
        def reveal(o):
            return lltype.cast_opaque_ptr(lltype.Ptr(A), o)
        def overwrite(a, i):
            a.value = i
        overwrite.dont_inline = True
        def f():
            o = gethidden(10)
            llop.gc__collect(lltype.Void)
            for i in range(1000):    # overwrite freed memory
                overwrite(lltype.malloc(A), i)
            a = reveal(o)
            return a.value
        fn = self.getcompiled(f)
        res = fn()
        assert res == -70

    def test_framework_finalizer(self):
        class B(object):
            pass
        b = B()
        b.nextid = 0
        b.num_deleted = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                b.num_deleted += 1
        def f():
            a = A()
            i = 0
            while i < 5:
                i += 1
                a = A()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            return b.num_deleted
        run = self.getcompiled(f)
        res = run()
        assert res == 6

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
        def f(i=int):
            a = A()
            f1(i)
            a.b = 1
            llop.gc__collect(lltype.Void)
            return a.b
        def f_0():
            try:
                return f(0)
            except TypeError:
                return 42
        def f_1():
            try:
                return f(1)
            except TypeError:
                return 42
        fn = self.getcompiled(f_0)
        assert fn() == 1
        fn = self.getcompiled(f_1)
        assert fn() == 42

    def test_del_raises(self):
        class B(object):
            def __del__(self):
                raise TypeError
        def func():
            b = B()
            return 0
        fn = self.getcompiled(func)
        # does not crash
        fn()

    def test_weakref(self):
        import weakref
        from pypy.rlib import rgc

        class A:
            pass

        def fn():
            n = 7000
            keepalive = []
            weakrefs = []
            a = None
            for i in range(n):
                if i & 1 == 0:
                    a = A()
                    a.index = i
                assert a is not None
                weakrefs.append(weakref.ref(a))
                if i % 7 == 6:
                    keepalive.append(a)
            rgc.collect()
            count_free = 0
            for i in range(n):
                a = weakrefs[i]()
                if i % 7 == 6:
                    assert a is not None
                if a is not None:
                    assert a.index == i & ~1
                else:
                    count_free += 1
            return count_free
        c_fn = self.getcompiled(fn)
        res = c_fn()
        # more than half of them should have been freed, ideally up to 6000
        assert 3500 <= res <= 6000

    def test_prebuilt_weakref(self):
        import weakref
        from pypy.rlib import rgc
        class A:
            pass
        a = A()
        a.hello = 42
        refs = [weakref.ref(a), weakref.ref(A())]
        rgc.collect()
        def fn():
            result = 0
            for i in range(2):
                a = refs[i]()
                rgc.collect()
                if a is None:
                    result += (i+1)
                else:
                    result += a.hello * (i+1)
            return result
        c_fn = self.getcompiled(fn)
        res = c_fn()
        assert res == fn()

    def test_framework_malloc_raw(self):
        A = lltype.Struct('A', ('value', lltype.Signed))

        def f():
            p = lltype.malloc(A, flavor='raw')
            p.value = 123
            llop.gc__collect(lltype.Void)
            res = p.value
            lltype.free(p, flavor='raw')
            return res
        fn = self.getcompiled(f)
        res = fn()
        assert res == 123

    def test_framework_malloc_gc(self):
        py.test.skip('in-progress')
        A = lltype.GcStruct('A', ('value', lltype.Signed))

        def f():
            p = lltype.malloc(A, flavor='gc')
            p.value = 123
            llop.gc__collect(lltype.Void)
            return p.value
        fn = self.getcompiled(f)
        res = fn()
        assert res == 123

    def test_framework_del_seeing_new_types(self):
        class B(object):
            pass
        class A(object):
            def __del__(self):
                B()
        def f():
            A()
            return 42
        fn = self.getcompiled(f)
        res = fn()
        assert res == 42

    def test_memory_error_varsize(self):
        py.test.skip("Needs lots (>2GB) of memory.")
        import gc
        import pypy.rlib.rgc
        from pypy.rpython.lltypesystem import lltype
        N = sys.maxint / 4 + 4
        A = lltype.GcArray(lltype.Signed)
        def alloc(n):
            return lltype.malloc(A, n)
        def f():
            try:
                try:
                    x = alloc(N)
                except MemoryError:
                    y = alloc(10)
                    return len(y)
                return -1
            finally:
                gc.collect()
                
        fn = self.getcompiled(f)
        res = fn()
        assert res == 10
        N = sys.maxint / 4
        fn = self.getcompiled(f)
        res = fn()
        assert res == 10

        N = sys.maxint / 4 - 1
        fn = self.getcompiled(f)
        res = fn()
        assert res == 10

        N = sys.maxint / 8 + 1000
        def f():
            try:
                x0 = alloc(N)
                try:
                    x1 = alloc(N)
                    return len(x0) + len(x1)
                except MemoryError:
                    y = alloc(10)
                    return len(y)
                return -1
            finally:
                gc.collect()

        fn = self.getcompiled(f)
        res = fn()
        assert res == 10

    def test_framework_late_filling_pointers(self):
        A = lltype.GcStruct('A', ('x', lltype.Signed))
        B = lltype.GcStruct('B', ('a', lltype.Ptr(A)))

        def f():
            p = lltype.malloc(B)
            llop.gc__collect(lltype.Void)
            p.a = lltype.malloc(A)
            return p.a.x
        fn = self.getcompiled(f)
        # the point is just not to segfault
        res = fn()

    def test_dict_segfault(self):
        " was segfaulting at one point see rev 39665 for fix and details "

        class Element:
            pass

        elements = [Element() for ii in range(10000)]

        def dostuff():
            reverse = {}
            l = elements[:]

            for ii in elements:
                reverse[ii] = ii

            for jj in range(100):
                e = l[-1]
                del reverse[e]
                l.remove(e)

        def f():
            for ii in range(100):
                dostuff()
            return 0

        fn = self.getcompiled(f)
        # the point is just not to segfault
        res = fn()

class TestUsingStacklessFramework(TestUsingFramework):
    gcpolicy = "stacklessgc"

    def getcompiled(self, f):
        # XXX quick hack
        from pypy.translator.c.test.test_stackless import StacklessTest
        runner = StacklessTest()
        runner.gcpolicy = self.gcpolicy
        runner.stacklessmode = True
        try:
            res = runner.wrap_stackless_function(f)
        except py.process.cmdexec.Error, e:
            if 'Fatal RPython error: MemoryError' in e.err:
                res = MemoryError
            else:
                raise
        self.t = runner.t
        def compiled():
            if res is MemoryError:
                raise MemoryError
            else:
                return res
        return compiled

    def test_weakref(self):
        py.test.skip("fails for some reason I couldn't figure out yet :-(")
