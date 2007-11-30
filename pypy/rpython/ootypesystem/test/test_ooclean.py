from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.test.test_llinterp import get_interpreter
import py
import sys


def check_only_ootype(graph):
    def check_ootype(v):
        t = v.concretetype
        assert isinstance(t, ootype.Primitive) or isinstance(t, ootype.OOType)
        
    for block in graph.iterblocks():
        for var in block.getvariables():
            check_ootype(var)
        for const in block.getconstants():
            check_ootype(const)

def interpret(func, values, view=False, viewbefore=False, policy=None,
              someobjects=False):
    interp, graph = get_interpreter(func, values, view, viewbefore, policy,
                             someobjects, type_system='ootype')
    for g in interp.typer.annotator.translator.graphs:
        check_only_ootype(g)
    return interp.eval_graph(graph, values)

# ____________________________________________________________

def test_simple():
    def f(a, b):
        return a + b
    result = interpret(f, [1, 2])
    assert result == 3

def test_simple_call():
    def f(a, b):
        return a + b

    def g():
        return f(5, 3)
    result = interpret(g, [])
    assert result == 8

# Adjusted from test_rclass.py
class EmptyBase(object):
    pass

def test_simple_empty_base():
    def dummyfn():
        x = EmptyBase()
        return x
    result = interpret(dummyfn, [])
    assert isinstance(ootype.typeOf(result), ootype.Instance)


def test_instance_attribute():
    def dummyfn():
        x = EmptyBase()
        x.a = 1
        return x.a
    result = interpret(dummyfn, [])
    assert result == 1

class Subclass(EmptyBase):
    pass

def test_subclass_attributes():
    def dummyfn():
        x = EmptyBase()
        x.a = 1
        y = Subclass()
        y.a = 2
        y.b = 3
        return x.a + y.a + y.b
    result = interpret(dummyfn, [])
    assert result == 1 + 2 + 3

def test_polymorphic_field():
    def dummyfn(choosesubclass):
        if choosesubclass:
            y = Subclass()
            y.a = 0
            y.b = 1
        else:
            y = EmptyBase()
            y.a = 1
        return y.a
    result = interpret(dummyfn, [True])
    assert result == 0
    result = interpret(dummyfn, [False])
    assert result == 1    

class HasAMethod(object):
    def f(self):
        return 1
        
def test_method():
    def dummyfn():
        inst = HasAMethod()
        return inst.f()
    result = interpret(dummyfn, [])
    assert result == 1

class OverridesAMethod(HasAMethod):
    def f(self):
        return 2

def test_override():
    def dummyfn(flag):
        if flag:
            inst = HasAMethod()
        else:
            inst = OverridesAMethod()
        return inst.f()
    result = interpret(dummyfn, [True])
    assert result == 1
    result = interpret(dummyfn, [False])
    assert result == 2

def test_method_used_in_subclasses_only():
    class A:
        def meth(self):
            return 123
    class B(A):
        pass
    def f():
        x = B()
        return x.meth()
    res = interpret(f, [])
    assert res == 123

def test_method_both_A_and_B():
    class A:
        def meth(self):
            return 123
    class B(A):
        pass
    def f():
        a = A()
        b = B()
        return a.meth() + b.meth()
    res = interpret(f, [])
    assert res == 246

class HasAField(object):
    def f(self):
        return self.a

def test_prebuilt_instance():
    inst = HasAField()
    inst.a = 3
    def dummyfn():
        return inst.f()
    result = interpret(dummyfn, [])
    assert result == 3

def test_recursive_prebuilt_instance():
    a = EmptyBase()
    b = EmptyBase()
    a.x = 5
    b.x = 6
    a.peer = b
    b.peer = a
    def dummyfn():
        return a.peer.peer.peer.x
    res = interpret(dummyfn, [])
    assert res == 6

def test_prebuilt_instances_with_void():
    def marker():
        return 42
    a = EmptyBase()
    a.nothing_special = marker
    def dummyfn():
        return a.nothing_special()
    res = interpret(dummyfn, [])
    assert res == 42

class HasClassAttr(object):
    a = 3
    def f(self, n):
        return n + self.a

class OverridesClassAttr(HasClassAttr):
    a = 42

def test_single_class_attr():
    def dummyfn():
        inst = HasClassAttr()
        return inst.f(100)
    result = interpret(dummyfn, [])
    assert result == 103

def test_class_attr():
    def dummyfn(flag):
        if flag:
            inst = HasClassAttr()
        else:
            inst = OverridesClassAttr()
        return inst.f(100)
    result = interpret(dummyfn, [True])
    assert result == 103
    result = interpret(dummyfn, [False])
    assert result == 142

def test_classattr_as_defaults():
    class MySubclass(HasClassAttr):
        pass
    def dummyfn():
        x = MySubclass()
        x.a += 1
        return x.a
    res = interpret(dummyfn, [])
    assert res == 4

def test_classattr_used_in_subclasses_only():
    class Subclass1(HasClassAttr):
        pass
    class Subclass2(HasClassAttr):
        pass
    class SubSubclass2(Subclass2):
        a = 5432
    def dummyfn(flag):
        inst1 = Subclass1()
        inst1.a += 42         # used as default
        if flag:
            inst2 = Subclass2()
        else:
            inst2 = SubSubclass2()
        return inst1.a + inst2.a
    res = interpret(dummyfn, [True])
    assert res == (3 + 42) + 3
    res = interpret(dummyfn, [False])
    assert res == (3 + 42) + 5432

def test_name_clashes():
    class NameClash1(object):
        def _TYPE(self):
            return 6
    def dummyfn(n):
        x = NameClash1()
        y = EmptyBase()
        y._TYPE = n+1
        return x._TYPE() * y._TYPE
    res = interpret(dummyfn, [6])
    assert res == 42

def test_null_instance():
    def dummyfn(flag):
        if flag:
            x = EmptyBase()
        else:
            x = None
        return not x
    res = interpret(dummyfn, [True])
    assert res is False
    res = interpret(dummyfn, [False])
    assert res is True

def test_isinstance():
    class A:
        pass
    class B(A):
        pass
    class C(B):
        pass
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
    res = interpret(f, [1])
    assert res == 100
    res = interpret(f, [2])
    assert res == 110
    res = interpret(f, [3])
    assert res == 111
    res = interpret(f, [0])
    assert res == 0

def test_issubclass_type():
    class A:
        pass
    class B(A):
        pass
    def f(i):
        if i == 0: 
            c1 = A()
        else: 
            c1 = B()
        return issubclass(type(c1), B)
    res = interpret(f, [0])
    assert res is False
    res = interpret(f, [1])
    assert res is True

    def g(i):
        if i == 0: 
            c1 = A()
        else: 
            c1 = B()
        return issubclass(type(c1), A)
    res = interpret(g, [0])
    assert res is True
    res = interpret(g, [1])
    assert res is True

def test_staticmethod():
    class A(object):
        f = staticmethod(lambda x, y: x*y)
    def f():
        a = A()
        return a.f(6, 7)
    res = interpret(f, [])
    assert res == 42

def test_instance_comparison():
    def f(flag):
        a = Subclass()
        if flag:
            b = a
        else:
            b = EmptyBase()
        return (a is b)*100 + (a == b)*10 + (a != b)
    res = interpret(f, [True])
    assert res == 110
    res = interpret(f, [False])
    assert res == 1

def test_is():
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
    res = interpret(f, [0])
    assert res == 0x0004
    res = interpret(f, [1])
    assert res == 0x0020
    res = interpret(f, [2])
    assert res == 0x0100
    res = interpret(f, [3])
    assert res == 0x0200

def test_eq():
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
    res = interpret(f, [0])
    assert res == 0x0004
    res = interpret(f, [1])
    assert res == 0x0020
    res = interpret(f, [2])
    assert res == 0x0100
    res = interpret(f, [3])
    assert res == 0x0200

def test_istrue():
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
    res = interpret(f, [0])
    assert res == 1
    res = interpret(f, [1])
    assert res == 2

def test_ne():
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
    res = interpret(f, [0])
    assert res == ~0x0004 & 0x3ff
    res = interpret(f, [1])
    assert res == ~0x0020 & 0x3ff
    res = interpret(f, [2])
    assert res == ~0x0100 & 0x3ff
    res = interpret(f, [3])
    assert res == ~0x0200 & 0x3ff

def test_hash_preservation():
    from pypy.rlib.objectmodel import current_object_addr_as_int
    class C:
        pass
    class D(C):
        pass
    def f1():
        d2 = D()
        # xxx we assume that the identityhash doesn't change from
        #     one line to the next
        current_identityhash = current_object_addr_as_int(d2)
        instance_hash = hash(d2)
        return ((current_identityhash & sys.maxint) ==
                (instance_hash & sys.maxint))
    res = interpret(f1, [])
    assert res is True

    c = C()
    d = D()
    def f2(): return hash(c)
    def f3(): return hash(d)
    res = interpret(f2, [])
    assert res == hash(c)
    res = interpret(f3, [])
    assert res == hash(d)

def test_type():
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
    res = interpret(f, [1])
    assert res is True
    res = interpret(f, [-1])
    assert res is False
    res = interpret(f, [0])
    assert res is False

def test_void_fnptr():
    def g():
        return 42
    def f():
        e = EmptyBase()
        e.attr = g
        return e.attr()
    res = interpret(f, [])
    assert res == 42

def test_abstract_base_method():
    class A(object):
        pass
    class B(A):
        def f(self):
            return 2
    class C(A):
        def f(self):
            return 3
    def f(flag):
        if flag:
            x = B()
        else:
            x = C()
        return x.f()
    res = interpret(f, [True])
    assert res == 2
    res = interpret(f, [False])
    assert res == 3
