from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.rarithmetic import intmask


class EmptyBase(object):
    pass

class Random:
    xyzzy = 12
    yadda = 21

# for method calls
class A:
    def f(self):
        return self.g()

    def g(self):
        return 42

class B(A):
    def g(self):
        return 1

class C(B):
    pass

class BaseTestRclass:

    def test_instanceattr(self):
        def dummyfn():
            x = EmptyBase()
            x.a = 5
            x.a += 1
            return x.a
        res = interpret(dummyfn, [], type_system=self.ts)
        assert res == 6

    def test_simple(self):
        def dummyfn():
            x = EmptyBase()
            return x
        res = interpret(dummyfn, [], type_system=self.ts)
        T = typeOf(res)
        if self.ts == "lltype":
            assert isinstance(T, Ptr) and isinstance(T.TO, GcStruct)
        else:
            assert isinstance(T, ootype.Instance)


    def test_classattr(self):
        def dummyfn():
            x = Random()
            return x.xyzzy
        res = interpret(dummyfn, [], type_system=self.ts)
        assert res == 12

    def test_classattr_both(self):
        class A:
            a = 1
        class B(A):
            a = 2
        def pick(i):
            if i == 0:
                return A
            else:
                return B
            
        def dummyfn(i):
            C = pick(i)
            i = C()
            return C.a + i.a
        res = interpret(dummyfn, [0], type_system=self.ts)
        assert res == 2
        res = interpret(dummyfn, [1], type_system=self.ts)
        assert res == 4

    def test_classattr_both2(self):
        class Base(object):
            a = 0
        class A(Base):
            a = 1
        class B(Base):
            a = 2
        def pick(i):
            if i == 0:
                return A
            else:
                return B
            
        def dummyfn(i):
            C = pick(i)
            i = C()
            return C.a + i.a
        res = interpret(dummyfn, [0], type_system=self.ts)
        assert res == 2
        res = interpret(dummyfn, [1], type_system=self.ts)
        assert res == 4

    def test_classattr_as_defaults(self):
        def dummyfn():
            x = Random()
            x.xyzzy += 1
            return x.xyzzy
        res = interpret(dummyfn, [], type_system=self.ts)
        assert res == 13

    def test_prebuilt_instance(self):
        a = EmptyBase()
        a.x = 5
        def dummyfn():
            a.x += 1
            return a.x
        interpret(dummyfn, [], type_system=self.ts)

    def test_recursive_prebuilt_instance(self):
        a = EmptyBase()
        b = EmptyBase()
        a.x = 5
        b.x = 6
        a.peer = b
        b.peer = a
        def dummyfn():
            return a.peer.peer.peer.x
        res = interpret(dummyfn, [], type_system=self.ts)
        assert res == 6

    def test_prebuilt_instances_with_void(self):
        def marker():
            return 42
        a = EmptyBase()
        a.nothing_special = marker
        def dummyfn():
            return a.nothing_special()
        res = interpret(dummyfn, [], type_system=self.ts)
        assert res == 42

    def test_simple_method_call(self):
        def f(i):
            if i:
                a = A()
            else:
                a = B()
            return a.f()
        res = interpret(f, [True], type_system=self.ts)
        assert res == 42
        res = interpret(f, [False], type_system=self.ts)
        assert res == 1

    def test_isinstance(self):
        def f(i):
            if i == 0:
                o = None
            elif i == 1:
                o = A()
            elif i == 2:
                o = B()
            else:
                o = C()
            return 100*isinstance(o, A)+10*isinstance(o, B)+1*isinstance(o ,C)

        res = interpret(f, [1], type_system=self.ts)
        assert res == 100
        res = interpret(f, [2], type_system=self.ts)
        assert res == 110
        res = interpret(f, [3], type_system=self.ts)
        assert res == 111

        res = interpret(f, [0], type_system=self.ts)
        assert res == 0

    def test_method_used_in_subclasses_only(self):
        class A:
            def meth(self):
                return 123
        class B(A):
            pass
        def f():
            x = B()
            return x.meth()
        res = interpret(f, [], type_system=self.ts)
        assert res == 123

    def test_method_both_A_and_B(self):
        class A:
            def meth(self):
                return 123
        class B(A):
            pass
        def f():
            a = A()
            b = B()
            return a.meth() + b.meth()
        res = interpret(f, [], type_system=self.ts)
        assert res == 246

    def test_issubclass_type(self):
        class Abstract:
            pass
        class A(Abstract):
            pass
        class B(A):
            pass
        def f(i):
            if i == 0: 
                c1 = A()
            else: 
                c1 = B()
            return issubclass(type(c1), B)
        assert interpret(f, [0], type_system=self.ts) == False 
        assert interpret(f, [1], type_system=self.ts) == True

        def g(i):
            if i == 0: 
                c1 = A()
            else: 
                c1 = B()
            return issubclass(type(c1), A)
        assert interpret(g, [0], type_system=self.ts) == True
        assert interpret(g, [1], type_system=self.ts) == True

    def test_staticmethod(self):
        class A(object):
            f = staticmethod(lambda x, y: x*y)
        def f():
            a = A()
            return a.f(6, 7)
        res = interpret(f, [], type_system=self.ts)
        assert res == 42

    def test_is(self):
        class A: pass
        class B(A): pass
        class C: pass
        def f(i):
            a = A()
            b = B()
            c = C()
            d = None
            e = None
            if i == 0:
                d = a
            elif i == 1:
                d = b
            elif i == 2:
                e = c
            return (0x0001*(a is b) | 0x0002*(a is c) | 0x0004*(a is d) |
                    0x0008*(a is e) | 0x0010*(b is c) | 0x0020*(b is d) |
                    0x0040*(b is e) | 0x0080*(c is d) | 0x0100*(c is e) |
                    0x0200*(d is e))
        res = interpret(f, [0], type_system=self.ts)
        assert res == 0x0004
        res = interpret(f, [1], type_system=self.ts)
        assert res == 0x0020
        res = interpret(f, [2], type_system=self.ts)
        assert res == 0x0100
        res = interpret(f, [3], type_system=self.ts)
        assert res == 0x0200

    def test_eq(self):
        class A: pass
        class B(A): pass
        class C: pass
        def f(i):
            a = A()
            b = B()
            c = C()
            d = None
            e = None
            if i == 0:
                d = a
            elif i == 1:
                d = b
            elif i == 2:
                e = c
            return (0x0001*(a == b) | 0x0002*(a == c) | 0x0004*(a == d) |
                    0x0008*(a == e) | 0x0010*(b == c) | 0x0020*(b == d) |
                    0x0040*(b == e) | 0x0080*(c == d) | 0x0100*(c == e) |
                    0x0200*(d == e))
        res = interpret(f, [0], type_system=self.ts)
        assert res == 0x0004
        res = interpret(f, [1], type_system=self.ts)
        assert res == 0x0020
        res = interpret(f, [2], type_system=self.ts)
        assert res == 0x0100
        res = interpret(f, [3])
        assert res == 0x0200

    def test_istrue(self):
        class A:
            pass
        def f(i):
            if i == 0:
                a = A()
            else:
                a = None
            if a:
                return 1
            else:
                return 2
        res = interpret(f, [0], type_system=self.ts)
        assert res == 1
        res = interpret(f, [1], type_system=self.ts)
        assert res == 2

    def test_ne(self):
        class A: pass
        class B(A): pass
        class C: pass
        def f(i):
            a = A()
            b = B()
            c = C()
            d = None
            e = None
            if i == 0:
                d = a
            elif i == 1:
                d = b
            elif i == 2:
                e = c
            return (0x0001*(a != b) | 0x0002*(a != c) | 0x0004*(a != d) |
                    0x0008*(a != e) | 0x0010*(b != c) | 0x0020*(b != d) |
                    0x0040*(b != e) | 0x0080*(c != d) | 0x0100*(c != e) |
                    0x0200*(d != e))
        res = interpret(f, [0], type_system=self.ts)
        assert res == ~0x0004 & 0x3ff
        res = interpret(f, [1], type_system=self.ts)
        assert res == ~0x0020 & 0x3ff
        res = interpret(f, [2], type_system=self.ts)
        assert res == ~0x0100 & 0x3ff
        res = interpret(f, [3], type_system=self.ts)
        assert res == ~0x0200 & 0x3ff

    def test_hash_preservation(self):
        class C:
            pass
        class D(C):
            pass
        c = C()
        d = D()
        def f():
            d2 = D()
            x = hash(d2) == id(d2) # xxx check for this CPython peculiarity for now
            return x, hash(c)+hash(d)

        res = interpret(f, [], type_system=self.ts)

        assert res.item0 == True
        assert res.item1 == intmask(hash(c)+hash(d))
        
    def test_type(self):
        class A:
            pass
        class B(A):
            pass
        def g(a):
            return type(a)
        def f(i):
            if i > 0:
                a = A()
            elif i < 0:
                a = B()
            else:
                a = None
            return g(a) is A    # should type(None) work?  returns None for now
        res = interpret(f, [1], type_system=self.ts)
        assert res is True
        res = interpret(f, [-1], type_system=self.ts)
        assert res is False
        res = interpret(f, [0], type_system=self.ts)
        assert res is False

    def test_void_fnptr(self):
        def g():
            return 42
        def f():
            e = EmptyBase()
            e.attr = g
            return e.attr()
        res = interpret(f, [], type_system=self.ts)
        assert res == 42

    def test_getattr_on_classes(self):
        class A:
            def meth(self):
                return self.value + 42
        class B(A):
            def meth(self):
                shouldnt**be**seen
        class C(B):
            def meth(self):
                return self.value - 1
        def pick_class(i):
            if i > 0:
                return A
            else:
                return C
        def f(i):
            meth = pick_class(i).meth
            x = C()
            x.value = 12
            return meth(x)   # calls A.meth or C.meth, completely ignores B.meth
        res = interpret(f, [1], type_system=self.ts)
        assert res == 54
        res = interpret(f, [0], type_system=self.ts)
        assert res == 11

    def test_constant_bound_method(self):
        class C:
            value = 1
            def meth(self):
                return self.value
        meth = C().meth
        def f():
            return meth()
        res = interpret(f, [], type_system=self.ts)
        assert res == 1

   

class TestLltype(BaseTestRclass):

    ts = "lltype"

    def test__del__(self):
        class A(object):
            def __init__(self):
                self.a = 2
            def __del__(self):
                self.a = 3
        def f():
            a = A()
            return a.a
        t = TranslationContext()
        t.buildannotator().build_types(f, [])
        t.buildrtyper().specialize()
        graph = graphof(t, f)
        TYPE = graph.startblock.operations[0].args[0].value
        RTTI = getRuntimeTypeInfo(TYPE)
        queryptr = RTTI._obj.query_funcptr # should not raise
        destrptr = RTTI._obj.destructor_funcptr
        assert destrptr is not None
    
    def test_del_inheritance(self):
        class State:
            pass
        s = State()
        s.a_dels = 0
        s.b_dels = 0
        class A(object):
            def __del__(self):
                s.a_dels += 1
        class B(A):
            def __del__(self):
                s.b_dels += 1
        class C(A):
            pass
        def f():
            A()
            B()
            C()
            A()
            B()
            C()
            return s.a_dels * 10 + s.b_dels
        res = f()
        assert res == 42
        t = TranslationContext()
        t.buildannotator().build_types(f, [])
        t.buildrtyper().specialize()
        graph = graphof(t, f)
        TYPEA = graph.startblock.operations[0].args[0].value
        RTTIA = getRuntimeTypeInfo(TYPEA)
        TYPEB = graph.startblock.operations[3].args[0].value
        RTTIB = getRuntimeTypeInfo(TYPEB)
        TYPEC = graph.startblock.operations[6].args[0].value
        RTTIC = getRuntimeTypeInfo(TYPEC)
        queryptra = RTTIA._obj.query_funcptr # should not raise
        queryptrb = RTTIB._obj.query_funcptr # should not raise
        queryptrc = RTTIC._obj.query_funcptr # should not raise
        destrptra = RTTIA._obj.destructor_funcptr
        destrptrb = RTTIB._obj.destructor_funcptr
        destrptrc = RTTIC._obj.destructor_funcptr
        assert destrptra == destrptrc
        assert typeOf(destrptra).TO.ARGS[0] != typeOf(destrptrb).TO.ARGS[0]
        assert destrptra is not None
        assert destrptrb is not None

class TestOotype(BaseTestRclass):

    ts = "ootype"

    def test__del__(self):
        class A(object):
            def __init__(self):
                self.a = 2
            def __del__(self):
                self.a = 3
        def f():
            a = A()
            return a.a
        t = TranslationContext()
        t.buildannotator().build_types(f, [])
        t.buildrtyper(type_system=self.ts).specialize()
        graph = graphof(t, f)
        TYPE = graph.startblock.operations[0].args[0].value
        _, meth = TYPE._lookup("o__del___variant0")
        assert meth.finalizer

    def test_del_inheritance(self):
        class State:
            pass
        s = State()
        s.a_dels = 0
        s.b_dels = 0
        class A(object):
            def __del__(self):
                s.a_dels += 1
        class B(A):
            def __del__(self):
                s.b_dels += 1
        class C(A):
            pass
        def f():
            A()
            B()
            C()
            A()
            B()
            C()
            return s.a_dels * 10 + s.b_dels
        res = f()
        assert res == 42
        t = TranslationContext()
        t.buildannotator().build_types(f, [])
        t.buildrtyper(type_system=self.ts).specialize()
        graph = graphof(t, f)
        TYPEA = graph.startblock.operations[0].args[0].value
        TYPEB = graph.startblock.operations[2].args[0].value
        TYPEC = graph.startblock.operations[4].args[0].value
        _, destra = TYPEA._lookup("o__del___variant0")
        _, destrb = TYPEB._lookup("o__del___variant0")
        _, destrc = TYPEC._lookup("o__del___variant0")
        assert destra == destrc
        assert destrb is not None
        assert destra is not None

