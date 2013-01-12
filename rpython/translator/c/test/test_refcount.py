import py
import os

from rpython.translator.translator import TranslationContext
from rpython.translator.c import genc
from rpython.translator.c.test.test_genc import compile
from rpython.rtyper.lltypesystem import lltype
from rpython.conftest import option

def compile_func(func, args):
    return compile(func, args, gcpolicy='ref')

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
    py.test.skip("xxx fix or kill")
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
    fn = compile_func(entrypoint, None, t)

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
    fn(1, expected_exception_name="TypeError")

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
