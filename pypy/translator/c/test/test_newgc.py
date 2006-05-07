import autopath
import sys
import py
from py.test import raises

from pypy.translator.translator import TranslationContext
from pypy.translator.backendopt.stat import print_statistics
from pypy.translator.c import genc, gc
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import cast_address_to_object, cast_object_to_address
from pypy.rpython.memory.gctransform import GCTransformer

from pypy import conftest

def compile_func(fn, inputtypes, t=None, gcpolicy=gc.RefcountingGcPolicy):
    if t is None:
        t = TranslationContext()
    if inputtypes is not None:
        t.buildannotator().build_types(fn, inputtypes)
        t.buildrtyper().specialize()
    builder = genc.CExtModuleBuilder(t, fn, gcpolicy=gcpolicy)
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
    for gcpolicy in [gc.RefcountingGcPolicy]:  #, gc.FrameworkGcPolicy]:
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

class Weakrefable(object):
    __lifeline__ = None

class Weakref(object):
    def __init__(self, obj):
        self.address = cast_object_to_address(obj)
    
    def ref(self):
        return cast_address_to_object(self.address, Weakrefable)

    def invalidate(self):
        from pypy.rpython.lltypesystem.llmemory import NULL
        self.address = NULL

class WeakrefLifeline(object):
    def __init__(self, obj):
        self.ref = Weakref(obj)
        
    def __del__(self):
        self.ref.invalidate()
    
    def get_weakref(self):
        return self.ref

def get_weakref(obj):
    assert isinstance(obj, Weakrefable)
    if obj.__lifeline__ is None:
        obj.__lifeline__ = WeakrefLifeline(obj)
    return obj.__lifeline__.get_weakref()

def test_weakref_alive():
    def func():
        f = Weakrefable()
        f.x = 32
        ref1 = get_weakref(f)
        ref2 = get_weakref(f)
        return f.x + ref2.ref().x + (ref1 is ref2)
    assert func() == 65
    f = compile_func(func, [])
    assert f() == 65

def test_weakref_dying():
    def g():
        f = Weakrefable()
        f.x = 32
        return get_weakref(f)
    def func():
        ref = g()
        return ref.ref() is None
    assert func()
    f = compile_func(func, [])
    assert f()

# _______________________________________________________________
# test framework

from pypy.translator.c.test.test_boehm import AbstractTestClass

class TestUsingFramework(AbstractTestClass):
    from pypy.translator.c.gc import FrameworkGcPolicy as gcpolicy

    def test_framework_simple(self):
        def g(x): # cannot cause a collect
            return x + 1
        class A(object):
            pass
        def f():
            a = A()
            a.b = g(1)
            # this should trigger a couple of collections
            # XXX make sure it triggers at least one somehow!
            for i in range(100000):
                [A()] * 1000
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
        def g(x): # can cause a collect
            return B()
        global_a = A()
        global_a.b = B()
        global_a.b.a = A()
        global_a.b.a.b = B()
        global_a.b.a.b.c = 1
        def f():
            global_a.b.a.b.c = 40
            a = global_a.b.a
            b = a.b
            b.c = 41
            g(1)
            b0 = a.b
            b0.c = b.c = 42
            # this should trigger a couple of collections
            # XXX make sure it triggers at least one somehow!
            for i in range(100000):
                [A()] * 1000
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
            # this should trigger 3 collections
            for i in range(1000000):
                prepare(B(), -1)
            # we need to prevent it getting inlined
            if not a:
                g(A())
            return a.value
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
        def f():
            a.x = A(42)
            for i in range(1000000):
                A(i)
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
            for i in range(1000000):
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
        
