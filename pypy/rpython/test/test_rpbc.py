from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.test.test_llinterp import interpret


def test_easy_call():
    def f(x):
        return x+1
    def g(y):
        return f(y+2)
    res = interpret(g, [5])
    assert res == 8

def test_multiple_call():
    def f1(x):
        return x+1
    def f2(x):
        return x+2
    def g(y):
        if y < 0:
            f = f1
        else:
            f = f2
        return f(y+3)
    res = interpret(g, [-1])
    assert res == 3
    res = interpret(g, [1])
    assert res == 6


class MyBase:
    def m(self, x):
        return self.z + x

class MySubclass(MyBase):
    def m(self, x):
        return self.z - x

class MyStrangerSubclass(MyBase):
    def m(self, x, y):
        return x*y

def test_method_call():
    def f(a, b):
        obj = MyBase()
        obj.z = a
        return obj.m(b)
    res = interpret(f, [4, 5])
    assert res == 9

def test_virtual_method_call():
    def f(a, b):
        if a > 0:
            obj = MyBase()
        else:
            obj = MySubclass()
        obj.z = a
        return obj.m(b)
    res = interpret(f, [1, 2.3])
    assert res == 3.3
    res = interpret(f, [-1, 2.3])
    assert res == -3.3

def test_stranger_subclass_1():
    def f1():
        obj = MyStrangerSubclass()
        obj.z = 100
        return obj.m(6, 7)
    res = interpret(f1, [])
    assert res == 42

def test_stranger_subclass_2():
    def f2():
        obj = MyStrangerSubclass()
        obj.z = 100
        return obj.m(6, 7) + MyBase.m(obj, 58)
    res = interpret(f2, [])
    assert res == 200


class MyBaseWithInit:
    def __init__(self, a):
        self.a1 = a

class MySubclassWithInit(MyBaseWithInit):
    def __init__(self, a, b):
        MyBaseWithInit.__init__(self, a)
        self.b1 = b

def test_class_init():
    def f(a):
        instance = MyBaseWithInit(a)
        return instance.a1
    assert interpret(f, [5]) == 5

def test_class_init_w_kwds():
    def f(a):
        instance = MyBaseWithInit(a=a)
        return instance.a1
    assert interpret(f, [5]) == 5

def test_class_init_2():
    def f(a, b):
        instance = MySubclassWithInit(a, b)
        return instance.a1 * instance.b1
    assert interpret(f, [6, 7]) == 42

def test_class_init_2_w_kwds():
    def f(a, b):
        instance = MySubclassWithInit(a, b=b)
        return instance.a1 * instance.b1
    assert interpret(f, [6, 7]) == 42

def test_class_calling_init():
    def f():
        instance = MySubclassWithInit(1, 2)
        instance.__init__(3, 4)
        return instance.a1 * instance.b1
    assert interpret(f, []) == 12


class Freezing:
    def _freeze_(self):
        return True
    def mymethod(self, y):
        return self.x + y

def test_freezing():
    fr1 = Freezing()
    fr2 = Freezing()
    fr1.x = 5
    fr2.x = 6
    def g(fr):
        return fr.x
    def f(n):
        if n > 0:
            fr = fr1
        elif n < 0:
            fr = fr2
        else:
            fr = None
        return g(fr)
    res = interpret(f, [1])
    assert res == 5
    res = interpret(f, [-1])
    assert res == 6

def test_call_frozen_pbc_simple():
    fr1 = Freezing()
    fr1.x = 5
    def f(n):
        return fr1.mymethod(n)
    res = interpret(f, [6])
    assert res == 11

def test_call_frozen_pbc_simple_w_kwds():
    fr1 = Freezing()
    fr1.x = 5
    def f(n):
        return fr1.mymethod(y=n)
    res = interpret(f, [6])
    assert res == 11

def test_call_frozen_pbc_multiple():
    fr1 = Freezing()
    fr2 = Freezing()
    fr1.x = 5
    fr2.x = 6
    def f(n):
        if n > 0:
            fr = fr1
        else:
            fr = fr2
        return fr.mymethod(n)
    res = interpret(f, [1])
    assert res == 6
    res = interpret(f, [-1])
    assert res == 5

def test_call_frozen_pbc_multiple_w_kwds():
    fr1 = Freezing()
    fr2 = Freezing()
    fr1.x = 5
    fr2.x = 6
    def f(n):
        if n > 0:
            fr = fr1
        else:
            fr = fr2
        return fr.mymethod(y=n)
    res = interpret(f, [1])
    assert res == 6
    res = interpret(f, [-1])
    assert res == 5

def test_is_among_frozen():
    fr1 = Freezing()
    fr2 = Freezing()
    def givefr1():
        return fr1
    def givefr2():
        return fr2
    def f(i):
        if i == 1:
            fr = givefr1()
        else:
            fr = givefr2()
        return fr is fr1
    res = interpret(f, [0])
    assert res is False
    res = interpret(f, [1])
    assert res is True

def test_unbound_method():
    def f():
        inst = MySubclass()
        inst.z = 40
        return MyBase.m(inst, 2)
    res = interpret(f, [])
    assert res == 42

def test_call_defaults():
    def g(a, b=2, c=3):
        return a+b+c
    def f1():
        return g(1)
    def f2():
        return g(1, 10)
    def f3():
        return g(1, 10, 100)
    res = interpret(f1, [])
    assert res == 1+2+3
    res = interpret(f2, [])
    assert res == 1+10+3
    res = interpret(f3, [])
    assert res == 1+10+100

def test_call_memoized_function():
    fr1 = Freezing()
    fr2 = Freezing()
    def getorbuild(key):
        a = 1
        if key is fr1:
            result = eval("a+2")
        else:
            result = eval("a+6")
        return result
    getorbuild._annspecialcase_ = "specialize:memo"

    def f1(i):
        if i > 0:
            fr = fr1
        else:
            fr = fr2
        return getorbuild(fr)

    res = interpret(f1, [0]) 
    assert res == 7
    res = interpret(f1, [1]) 
    assert res == 3

def test_call_memoized_cache():

    # this test checks that we add a separate field 
    # per specialization and also it uses a subclass of 
    # the standard pypy.tool.cache.Cache

    from pypy.tool.cache import Cache
    fr1 = Freezing()
    fr2 = Freezing()

    class Cache1(Cache): 
        def _build(self, key): 
            "NOT_RPYTHON" 
            if key is fr1:
                return fr2 
            else:
                return fr1 

    class Cache2(Cache): 
        def _build(self, key): 
            "NOT_RPYTHON" 
            a = 1
            if key is fr1:
                result = eval("a+2")
            else:
                result = eval("a+6")
            return result

    cache1 = Cache1()
    cache2 = Cache2()

    def f1(i):
        if i > 0:
            fr = fr1
        else:
            fr = fr2
        newfr = cache1.getorbuild(fr)
        return cache2.getorbuild(newfr)

    res = interpret(f1, [0], view=0, viewbefore=0)  
    assert res == 3
    res = interpret(f1, [1]) 
    assert res == 7

def test_call_memo_with_class():
    class A: pass
    class FooBar(A): pass
    def memofn(cls):
        return len(cls.__name__)
    memofn._annspecialcase_ = "specialize:memo"

    def f1(i):
        if i == 1:
            cls = A
        else:
            cls = FooBar
        FooBar()    # make sure we have ClassDefs
        return memofn(cls)
    res = interpret(f1, [1])
    assert res == 1
    res = interpret(f1, [2])
    assert res == 6

def test_call_memo_with_single_value():
    class A: pass
    def memofn(cls):
        return len(cls.__name__)
    memofn._annspecialcase_ = "specialize:memo"

    def f1():
        A()    # make sure we have a ClassDef
        return memofn(A)
    res = interpret(f1, [])
    assert res == 1

def test_rpbc_bound_method_static_call():
    class R:
        def meth(self):
            return 0
    r = R()
    m = r.meth
    def fn():
        return m()
    res = interpret(fn, [])
    assert res == 0

def test_rpbc_bound_method_static_call_w_kwds():
    class R:
        def meth(self, x):
            return x
    r = R()
    m = r.meth
    def fn():
        return m(x=3)
    res = interpret(fn, [])
    assert res == 3


def test_constant_return_disagreement():
    class R:
        def meth(self):
            return 0
    r = R()
    def fn():
        return r.meth()
    res = interpret(fn, [])
    assert res == 0

def test_None_is_false():
    def fn(i):
        return bool([None, fn][i])
    res = interpret(fn, [1])
    assert res is True
    res = interpret(fn, [0])
    assert res is False

def test_classpbc_getattr():
    class A:
        myvalue = 123
    class B(A):
        myvalue = 456
    def f(i):
        return [A,B][i].myvalue
    res = interpret(f, [0])
    assert res == 123
    res = interpret(f, [1])
    assert res == 456

def test_function_or_None():
    def g1():
        return 42
    def f(i):
        g = None
        if i > 5:
            g = g1
        if i > 6:
            return g()
        else:
            return 12

    res = interpret(f, [0])
    assert res == 12
    res = interpret(f, [6])
    assert res == 12
    res = interpret(f, [7])
    assert res == 42

def test_classdef_getattr():
    class A:
        myvalue = 123
    class B(A):
        myvalue = 456
    def f(i):
        B()    # for A and B to have classdefs
        return [A,B][i].myvalue
    res = interpret(f, [0])
    assert res == 123
    res = interpret(f, [1])
    assert res == 456

def test_call_classes():
    class A: pass
    class B(A): pass
    def f(i):
        if i == 1:
            cls = B
        else:
            cls = A
        return cls()
    res = interpret(f, [0])
    assert res.super.typeptr.name[0] == 'A'
    res = interpret(f, [1])
    assert res.super.typeptr.name[0] == 'B'

def test_call_classes_with_init2():
    class A:
        def __init__(self, z):
            self.z = z
    class B(A):
        def __init__(self, z, x=42):
            A.__init__(self, z)
            self.extra = x
    def f(i, z):
        if i == 1:
            cls = B
        else:
            cls = A
        return cls(z)
    res = interpret(f, [0, 5])
    assert res.super.typeptr.name[0] == 'A'
    assert res.inst_z == 5
    res = interpret(f, [1, -7645])
    assert res.super.typeptr.name[0] == 'B'
    assert res.inst_z == -7645
    assert res._obj._parentstructure().inst_extra == 42

def test_call_starargs():
    def g(x=-100, *arg):
        return x + len(arg)
    def f(i):
        if i == -1:
            return g()
        elif i == 0:
            return g(4)
        elif i == 1:
            return g(5, 15)
        elif i == 2:
            return g(7, 17, 27)
        else:
            return g(10, 198, 1129, 13984)
    res = interpret(f, [-1])
    assert res == -100
    res = interpret(f, [0])
    assert res == 4
    res = interpret(f, [1])
    assert res == 6
    res = interpret(f, [2])
    assert res == 9
    res = interpret(f, [3])
    assert res == 13

def test_conv_from_None():
    class A(object): pass
    def none():
        return None
    
    def f(i):
        if i == 1:
            return none()
        else:
            return "ab"
    res = interpret(f, [1])
    assert not res
    res = interpret(f, [0])
    assert ''.join(res.chars) == "ab"
        
    def g(i):
        if i == 1:
            return none()
        else:
            return A()
    res = interpret(g, [1])
    assert not res
    res = interpret(g, [0])
    assert res.super.typeptr.name[0] == 'A'

    
def test_conv_from_classpbcset_to_larger():
    class A(object): pass
    class B(A): pass
    class C(A): pass

    def a():
        return A
    def b():
        return B
    

    def g(i):
        if i == 1:
            cls = a()
        else:
            cls = b()
        return cls()

    res = interpret(g, [0])
    assert res.super.typeptr.name[0] == 'B'
    res = interpret(g, [1])
    assert res.super.typeptr.name[0] == 'A'

    def bc(j):
        if j == 1:
            return B
        else:
            return C

    def g(i, j):
        if i == 1:
            cls = a()
        else:
            cls = bc(j)
        return cls()

    res = interpret(g, [0, 0])
    assert res.super.typeptr.name[0] == 'C'
    res = interpret(g, [0, 1])
    assert res.super.typeptr.name[0] == 'B'    
    res = interpret(g, [1, 0])
    assert res.super.typeptr.name[0] == 'A'    
    
def test_call_keywords():
    def g(a=1, b=2, c=3):
        return 100*a+10*b+c

    def f(i):
        if i == 0:
            return g(a=7)
        elif i == 1:
            return g(b=11)
        elif i == 2:
            return g(c=13)
        elif i == 3:
            return g(a=7, b=11)
        elif i == 4:
            return g(b=7, a=11)
        elif i == 5:
            return g(a=7, c=13)
        elif i == 6:
            return g(c=7, a=13)
        elif i == 7:
            return g(a=7,b=11,c=13)
        elif i == 8:
            return g(a=7,c=11,b=13)
        elif i == 9:
            return g(b=7,a=11,c=13)
        else:
            return g(b=7,c=11,a=13)

    for i in range(11):
        res = interpret(f, [i])
        assert res == f(i)

def test_call_star_and_keywords():
    def g(a=1, b=2, c=3):
        return 100*a+10*b+c

    def f(i, x):
        if x == 1:
            j = 11
        else:
            j = 22
        if i == 0:
            return g(7)
        elif i == 1:
            return g(7,*(j,))
        elif i == 2:
            return g(7,*(11,j))
        elif i == 3:
            return g(a=7)
        elif i == 4:
            return g(b=7, *(j,))
        elif i == 5:
            return g(b=7, c=13, *(j,))
        elif i == 6:
            return g(c=7, b=13, *(j,))
        elif i == 7:
            return g(c=7,*(j,))
        elif i == 8:
            return g(c=7,*(11,j))
        else:
            return 0

    for i in range(9):
        for x in range(1):
            res = interpret(f, [i, x])
            assert res == f(i, x)

def test_call_star_and_keywords_starargs():
    def g(a=1, b=2, c=3, *rest):
        return 1000*len(rest)+100*a+10*b+c

    def f(i, x):
        if x == 1:
            j = 13
        else:
            j = 31
        if i == 0:
            return g()
        elif i == 1:
            return g(*(j,))
        elif i == 2:
            return g(*(13, j))
        elif i == 3:
            return g(*(13, j, 19))
        elif i == 4:
            return g(*(13, j, 19, 21))
        elif i == 5:
            return g(7)
        elif i == 6:
            return g(7, *(j,))
        elif i == 7:
            return g(7, *(13, j))
        elif i == 8:
            return g(7, *(13, 17, j))
        elif i == 9:
            return g(7, *(13, 17, j, 21))
        elif i == 10:
            return g(7, 9)
        elif i == 11:
            return g(7, 9, *(j,))
        elif i == 12:
            return g(7, 9, *(j, 17))
        elif i == 13:
            return g(7, 9, *(13, j, 19))
        elif i == 14:
            return g(7, 9, 11)
        elif i == 15:
            return g(7, 9, 11, *(j,))
        elif i == 16:
            return g(7, 9, 11, *(13, j))
        elif i == 17:
            return g(7, 9, 11, *(13, 17, j))
        elif i == 18:
            return g(7, 9, 11, 2)
        elif i == 19:
            return g(7, 9, 11, 2, *(j,))
        elif i == 20:
            return g(7, 9, 11, 2, *(13, j))
        else:
            return 0

    for i in range(21):
        for x in range(1):
            res = interpret(f, [i, x])
            assert res == f(i, x)

def test_conv_from_funcpbcset_to_larger():
    def f1():
        return 7
    def f2():
        return 11
    def f3():
        return 13

    def a():
        return f1
    def b():
        return f2
    

    def g(i):
        if i == 1:
            f = a()
        else:
            f = b()
        return f()

    res = interpret(g, [0])
    assert res == 11
    res = interpret(g, [1])
    assert res == 7

    def bc(j):
        if j == 1:
            return f2
        else:
            return f3

    def g(i, j):
        if i == 1:
            cls = a()
        else:
            cls = bc(j)
        return cls()

    res = interpret(g, [0, 0])
    assert res == 13
    res = interpret(g, [0, 1])
    assert res == 11
    res = interpret(g, [1, 0])
    assert res == 7

def test_call_special_starargs_method():
    class Star:
        def __init__(self, d):
            self.d = d
        def meth(self, *args):
            return self.d + len(args)

    def f(i, j):
        s = Star(i)
        return s.meth(i, j)

    res = interpret(f, [3, 0])
    assert res == 5
