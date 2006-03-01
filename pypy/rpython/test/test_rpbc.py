from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.test.test_llinterp import interpret


class MyBase:
    def m(self, x):
        return self.z + x

class MySubclass(MyBase):
    def m(self, x):
        return self.z - x

class MyStrangerSubclass(MyBase):
    def m(self, x, y):
        return x*y

class MyBaseWithInit:
    def __init__(self, a):
        self.a1 = a

class MySubclassWithInit(MyBaseWithInit):
    def __init__(self, a, b):
        MyBaseWithInit.__init__(self, a)
        self.b1 = b

class Freezing:
    def _freeze_(self):
        return True
    def mymethod(self, y):
        return self.x + y


class BaseTestRPBC:

    def test_easy_call(self):
        def f(x):
            return x+1
        def g(y):
            return f(y+2)
        res = interpret(g, [5], type_system=self.ts)
        assert res == 8

    def test_multiple_call(self):
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
        res = interpret(g, [-1], type_system=self.ts)
        assert res == 3
        res = interpret(g, [1], type_system=self.ts)
        assert res == 6


    def test_method_call(self):
        def f(a, b):
            obj = MyBase()
            obj.z = a
            return obj.m(b)
        res = interpret(f, [4, 5], type_system=self.ts)
        assert res == 9

    def test_virtual_method_call(self):
        def f(a, b):
            if a > 0:
                obj = MyBase()
            else:
                obj = MySubclass()
            obj.z = a
            return obj.m(b)
        res = interpret(f, [1, 2.3], type_system=self.ts)
        assert res == 3.3
        res = interpret(f, [-1, 2.3], type_system=self.ts)
        assert res == -3.3

    def test_stranger_subclass_1(self):
        def f1():
            obj = MyStrangerSubclass()
            obj.z = 100
            return obj.m(6, 7)
        res = interpret(f1, [], type_system=self.ts)
        assert res == 42

    def test_stranger_subclass_2(self):
        def f2():
            obj = MyStrangerSubclass()
            obj.z = 100
            return obj.m(6, 7) + MyBase.m(obj, 58)
        res = interpret(f2, [], type_system=self.ts)
        assert res == 200


    def test_class_init(self):
        def f(a):
            instance = MyBaseWithInit(a)
            return instance.a1
        assert interpret(f, [5], type_system=self.ts) == 5

    def test_class_init_2(self):
        def f(a, b):
            instance = MySubclassWithInit(a, b)
            return instance.a1 * instance.b1
        assert interpret(f, [6, 7], type_system=self.ts) == 42

    def test_class_calling_init(self):
        def f():
            instance = MySubclassWithInit(1, 2)
            instance.__init__(3, 4)
            return instance.a1 * instance.b1
        assert interpret(f, [], type_system=self.ts) == 12

    def test_class_init_w_kwds(self):
        def f(a):
            instance = MyBaseWithInit(a=a)
            return instance.a1
        assert interpret(f, [5], type_system=self.ts) == 5

    def test_class_init_2_w_kwds(self):
        def f(a, b):
            instance = MySubclassWithInit(a, b=b)
            return instance.a1 * instance.b1
        assert interpret(f, [6, 7], type_system=self.ts) == 42


    def test_freezing(self):
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
        res = interpret(f, [1], type_system=self.ts)
        assert res == 5
        res = interpret(f, [-1], type_system=self.ts)
        assert res == 6

    def test_call_frozen_pbc_simple(self):
        fr1 = Freezing()
        fr1.x = 5
        def f(n):
            return fr1.mymethod(n)
        res = interpret(f, [6], type_system=self.ts)
        assert res == 11

    def test_call_frozen_pbc_simple_w_kwds(self):
        fr1 = Freezing()
        fr1.x = 5
        def f(n):
            return fr1.mymethod(y=n)
        res = interpret(f, [6], type_system=self.ts)
        assert res == 11

    def test_call_frozen_pbc_multiple(self):
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
        res = interpret(f, [1], type_system=self.ts)
        assert res == 6
        res = interpret(f, [-1], type_system=self.ts)
        assert res == 5

    def test_call_frozen_pbc_multiple_w_kwds(self):
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
        res = interpret(f, [1], type_system=self.ts)
        assert res == 6
        res = interpret(f, [-1], type_system=self.ts)
        assert res == 5

    def test_is_among_frozen(self):
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
        res = interpret(f, [0], type_system=self.ts)
        assert res is False
        res = interpret(f, [1], type_system=self.ts)
        assert res is True

    def test_unbound_method(self):
        def f():
            inst = MySubclass()
            inst.z = 40
            return MyBase.m(inst, 2)
        res = interpret(f, [], type_system=self.ts)
        assert res == 42

    def test_call_defaults(self):
        def g(a, b=2, c=3):
            return a+b+c
        def f1():
            return g(1)
        def f2():
            return g(1, 10)
        def f3():
            return g(1, 10, 100)
        res = interpret(f1, [], type_system=self.ts)
        assert res == 1+2+3
        res = interpret(f2, [], type_system=self.ts)
        assert res == 1+10+3
        res = interpret(f3, [], type_system=self.ts)
        assert res == 1+10+100

    def test_call_memoized_function(self):
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

        res = interpret(f1, [0], type_system=self.ts) 
        assert res == 7
        res = interpret(f1, [1], type_system=self.ts) 
        assert res == 3

    def test_call_memoized_function_with_bools(self):
        fr1 = Freezing()
        fr2 = Freezing()
        def getorbuild(key, flag1, flag2):
            a = 1
            if key is fr1:
                result = eval("a+2")
            else:
                result = eval("a+6")
            if flag1:
                result += 100
            if flag2:
                result += 1000
            return result
        getorbuild._annspecialcase_ = "specialize:memo"

        def f1(i):
            if i > 0:
                fr = fr1
            else:
                fr = fr2
            return getorbuild(fr, i % 2 == 0, i % 3 == 0)

        for n in [0, 1, 2, -3, 6]:
            res = interpret(f1, [n], type_system=self.ts)
            assert res == f1(n)

    def test_call_memoized_cache(self):

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

        res = interpret(f1, [0], type_system=self.ts)  
        assert res == 3
        res = interpret(f1, [1], type_system=self.ts) 
        assert res == 7

    def test_call_memo_with_single_value(self):
        class A: pass
        def memofn(cls):
            return len(cls.__name__)
        memofn._annspecialcase_ = "specialize:memo"

        def f1():
            A()    # make sure we have a ClassDef
            return memofn(A)
        res = interpret(f1, [], type_system=self.ts)
        assert res == 1

    def test_call_memo_with_class(self):
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
        res = interpret(f1, [1], type_system=self.ts)
        assert res == 1
        res = interpret(f1, [2], type_system=self.ts)
        assert res == 6

    def test_rpbc_bound_method_static_call(self):
        class R:
            def meth(self):
                return 0
        r = R()
        m = r.meth
        def fn():
            return m()
        res = interpret(fn, [], type_system=self.ts)
        assert res == 0

    def test_rpbc_bound_method_static_call_w_kwds(self):
        class R:
            def meth(self, x):
                return x
        r = R()
        m = r.meth
        def fn():
            return m(x=3)
        res = interpret(fn, [], type_system=self.ts)
        assert res == 3


    def test_constant_return_disagreement(self):
        class R:
            def meth(self):
                return 0
        r = R()
        def fn():
            return r.meth()
        res = interpret(fn, [], type_system=self.ts)
        assert res == 0

    def test_None_is_false(self):
        def fn(i):
            if i == 0:
                v = None
            else:
                v = fn
            return bool(v)
        res = interpret(fn, [1], type_system=self.ts)
        assert res is True
        res = interpret(fn, [0], type_system=self.ts)
        assert res is False

    def test_classpbc_getattr(self):
        class A:
            myvalue = 123
        class B(A):
            myvalue = 456
        def f(i):
            if i == 0:
                v = A
            else:
                v = B
            return v.myvalue
        res = interpret(f, [0], type_system=self.ts)
        assert res == 123
        res = interpret(f, [1], type_system=self.ts)
        assert res == 456

    def test_function_or_None(self):
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

        res = interpret(f, [0], type_system=self.ts)
        assert res == 12
        res = interpret(f, [6], type_system=self.ts)
        assert res == 12
        res = interpret(f, [7], type_system=self.ts)
        assert res == 42

    def test_classdef_getattr(self):
        class A:
            myvalue = 123
        class B(A):
            myvalue = 456
        def f(i):
            B()    # for A and B to have classdefs
            if i == 0:
                v = A
            else:
                v = B
            return v.myvalue
        res = interpret(f, [0], type_system=self.ts)
        assert res == 123
        res = interpret(f, [1], type_system=self.ts)
        assert res == 456

    def test_call_classes(self):
        class A: pass
        class B(A): pass
        def f(i):
            if i == 1:
                cls = B
            else:
                cls = A
            return cls()
        res = interpret(f, [0], type_system=self.ts)
        assert self.class_name(res) == 'A'
        res = interpret(f, [1], type_system=self.ts)
        assert self.class_name(res) == 'B'

    def test_call_classes_with_init2(self):
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
        res = interpret(f, [0, 5], type_system=self.ts)
        assert self.class_name(res) == 'A'
        assert self.read_attr(res, "z") == 5
        res = interpret(f, [1, -7645], type_system=self.ts)
        assert self.class_name(res) == 'B'
        assert self.read_attr(res, "z") == -7645
        assert self.read_attr(res, "extra") == 42

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

def test_call_star_method():
    class N:
        def __init__(self, d):
            self.d = d
        def meth(self, a, b):
            return self.d + a + b

    def f(i, j):
        n = N(i)
        return n.meth(*(i, j))

    res = interpret(f, [3, 7])
    assert res == 13

def test_call_star_special_starargs_method():
    class N:
        def __init__(self, d):
            self.d = d
        def meth(self, *args):
            return self.d + len(args)

    def f(i, j):
        n = N(i)
        return n.meth(*(i, j))

    res = interpret(f, [3, 0])
    assert res == 5

def test_various_patterns_but_one_signature_method():
    class A:
        def meth(self, a, b=0):
            raise NotImplementedError
    class B(A):
        def meth(self, a, b=0):
            return a+b
        
    class C(A):
        def meth(self, a, b=0):
            return a*b
    def f(i):
        if i == 0:
            x = B()
        else:
            x = C()
        r1 = x.meth(1)
        r2 = x.meth(3, 2)
        r3 = x.meth(7, b=11)
        return r1+r2+r3
    res = interpret(f, [0])
    assert res == 1+3+2+7+11
    res = interpret(f, [1])
    assert res == 3*2+11*7
    

def test_multiple_ll_one_hl_op():
    class E(Exception):
        pass
    class A(object):
        pass
    class B(A):
        pass
    class C(object):
        def method(self, x):
            if x:
                raise E()
            else:
                return A()
    class D(C):
        def method(self, x):
            if x:
                raise E()
            else:
                return B()
    def call(x):
        c = D()
        c.method(x)
        try:
            c.method(x + 1)
        except E:
            pass
        c = C()
        c.method(x)
        try:
            return c.method(x + 1)
        except E:
            return None
    res = interpret(call, [0])

def test_multiple_pbc_with_void_attr():
    class A:
        def _freeze_(self):
            return True
    a1 = A()
    a2 = A()
    unique = A()
    unique.result = 42
    a1.value = unique
    a2.value = unique
    def g(a):
        return a.value.result
    def f(i):
        if i == 1:
            a = a1
        else:
            a = a2
        return g(a)
    res = interpret(f, [0])
    assert res == 42
    res = interpret(f, [1])
    assert res == 42

def test_hlinvoke_simple():
    def f(a,b):
        return a + b
    from pypy.translator import translator
    from pypy.annotation import annrpython
    a = annrpython.RPythonAnnotator()
    from pypy.annotation import model as annmodel
    
    s_f = a.bookkeeper.immutablevalue(f) 
    a.bookkeeper.emulate_pbc_call('f', s_f, [annmodel.SomeInteger(), annmodel.SomeInteger()])
    a.complete()

    from pypy.rpython import rtyper
    rt = rtyper.RPythonTyper(a)
    rt.specialize()

    def ll_h(R, f, x):
        from pypy.rpython.objectmodel import hlinvoke
        return hlinvoke(R, f, x, 2)

    from pypy.rpython import annlowlevel

    r_f = rt.getrepr(s_f)

    s_R = a.bookkeeper.immutablevalue(r_f)
    s_ll_f = annmodel.lltype_to_annotation(r_f.lowleveltype)
    ll_h_graph = annlowlevel.annotate_lowlevel_helper(a, ll_h, [s_R, s_ll_f, annmodel.SomeInteger()])
    assert a.binding(ll_h_graph.getreturnvar()).knowntype == int
    rt.specialize_more_blocks()

    from pypy.rpython.llinterp import LLInterpreter
    interp = LLInterpreter(rt)

    #a.translator.view()
    res = interp.eval_graph(ll_h_graph, [None, None, 3])
    assert res == 5

def test_hlinvoke_simple2():
    def f1(a,b):
        return a + b
    def f2(a,b):
        return a - b
    from pypy.annotation import annrpython
    a = annrpython.RPythonAnnotator()
    from pypy.annotation import model as annmodel
    
    def g(i):
        if i:
            f = f1
        else:
            f = f2
        f(5,4)
        f(3,2)
        
    a.build_types(g, [int])

    from pypy.rpython import rtyper
    rt = rtyper.RPythonTyper(a)
    rt.specialize()

    def ll_h(R, f, x):
        from pypy.rpython.objectmodel import hlinvoke
        return hlinvoke(R, f, x, 2)

    from pypy.rpython import annlowlevel

    f1desc = a.bookkeeper.getdesc(f1)
    f2desc = a.bookkeeper.getdesc(f2)

    s_f = annmodel.SomePBC([f1desc, f2desc])
    r_f = rt.getrepr(s_f)

    s_R = a.bookkeeper.immutablevalue(r_f)
    s_ll_f = annmodel.lltype_to_annotation(r_f.lowleveltype)
    ll_h_graph= annlowlevel.annotate_lowlevel_helper(a, ll_h, [s_R, s_ll_f, annmodel.SomeInteger()])
    assert a.binding(ll_h_graph.getreturnvar()).knowntype == int
    rt.specialize_more_blocks()

    from pypy.rpython.llinterp import LLInterpreter
    interp = LLInterpreter(rt)

    #a.translator.view()
    res = interp.eval_graph(ll_h_graph, [None, r_f.convert_desc(f1desc), 3])
    assert res == 5
    res = interp.eval_graph(ll_h_graph, [None, r_f.convert_desc(f2desc), 3])
    assert res == 1


def test_hlinvoke_hltype():
    class A(object):
        def __init__(self, v):
            self.v = v
    def f(a):
        return A(a)

    from pypy.annotation import annrpython
    a = annrpython.RPythonAnnotator()
    from pypy.annotation import model as annmodel

    def g():
        a = A(None)
        f(a)

    a.build_types(g, [])

    from pypy.rpython import rtyper
    from pypy.rpython import rclass
    rt = rtyper.RPythonTyper(a)
    rt.specialize()

    def ll_h(R, f, a):
        from pypy.rpython.objectmodel import hlinvoke
        return hlinvoke(R, f, a)

    from pypy.rpython import annlowlevel

    s_f = a.bookkeeper.immutablevalue(f)
    r_f = rt.getrepr(s_f)

    s_R = a.bookkeeper.immutablevalue(r_f)
    s_ll_f = annmodel.lltype_to_annotation(r_f.lowleveltype)
    A_repr = rclass.getinstancerepr(rt, a.bookkeeper.getdesc(A).
                                    getuniqueclassdef())
    ll_h_graph = annlowlevel.annotate_lowlevel_helper(a, ll_h, [s_R, s_ll_f, annmodel.SomePtr(A_repr.lowleveltype)])
    s = a.binding(ll_h_graph.getreturnvar())
    assert s.ll_ptrtype == A_repr.lowleveltype
    rt.specialize_more_blocks()
    
    from pypy.rpython.llinterp import LLInterpreter
    interp = LLInterpreter(rt)
    
    #a.translator.view()
    c_a = A_repr.convert_const(A(None))
    res = interp.eval_graph(ll_h_graph, [None, None, c_a])
    assert typeOf(res) == A_repr.lowleveltype

def test_hlinvoke_method_hltype():
    class A(object):
        def __init__(self, v):
            self.v = v
    class Impl(object):
        def f(self, a):
            return A(a)

    from pypy.annotation import annrpython
    a = annrpython.RPythonAnnotator()
    from pypy.annotation import model as annmodel

    def g():
        a = A(None)
        i = Impl()
        i.f(a)

    a.build_types(g, [])

    from pypy.rpython import rtyper
    from pypy.rpython import rclass
    rt = rtyper.RPythonTyper(a)
    rt.specialize()

    def ll_h(R, f, a):
        from pypy.rpython.objectmodel import hlinvoke
        return hlinvoke(R, f, a)

    from pypy.rpython import annlowlevel

    Impl_def = a.bookkeeper.getdesc(Impl).getuniqueclassdef()
    Impl_f_desc = a.bookkeeper.getmethoddesc(
        a.bookkeeper.getdesc(Impl.f.im_func),
        Impl_def,
        Impl_def,
        'f')
    s_f = annmodel.SomePBC([Impl_f_desc])
    r_f = rt.getrepr(s_f)

    s_R = a.bookkeeper.immutablevalue(r_f)
    s_ll_f = annmodel.lltype_to_annotation(r_f.lowleveltype)
    A_repr = rclass.getinstancerepr(rt, a.bookkeeper.getdesc(A).
                                    getuniqueclassdef()) 
    ll_h_graph = annlowlevel.annotate_lowlevel_helper(a, ll_h, [s_R, s_ll_f, annmodel.SomePtr(A_repr.lowleveltype)])
    s = a.binding(ll_h_graph.getreturnvar())
    assert s.ll_ptrtype == A_repr.lowleveltype
    rt.specialize_more_blocks()

    from pypy.rpython.llinterp import LLInterpreter    
    interp = LLInterpreter(rt)
    
    # low-level value is just the instance
    c_f = rclass.getinstancerepr(rt, Impl_def).convert_const(Impl())
    c_a = A_repr.convert_const(A(None))
    res = interp.eval_graph(ll_h_graph, [None, c_f, c_a])
    assert typeOf(res) == A_repr.lowleveltype

def test_hlinvoke_pbc_method_hltype():
    class A(object):
        def __init__(self, v):
            self.v = v
    class Impl(object):
        def _freeze_(self):
            return True

        def f(self, a):
            return A(a)

    from pypy.annotation import annrpython
    a = annrpython.RPythonAnnotator()
    from pypy.annotation import model as annmodel

    i = Impl()

    def g():
        a = A(None)
        i.f(a)

    a.build_types(g, [])

    from pypy.rpython import rtyper
    from pypy.rpython import rclass
    rt = rtyper.RPythonTyper(a)
    rt.specialize()

    def ll_h(R, f, a):
        from pypy.rpython.objectmodel import hlinvoke
        return hlinvoke(R, f, a)

    from pypy.rpython import annlowlevel

    s_f = a.bookkeeper.immutablevalue(i.f)
    r_f = rt.getrepr(s_f)

    s_R = a.bookkeeper.immutablevalue(r_f)
    s_ll_f = annmodel.lltype_to_annotation(r_f.lowleveltype)

    A_repr = rclass.getinstancerepr(rt, a.bookkeeper.getdesc(A).
                                    getuniqueclassdef())
    ll_h_graph = annlowlevel.annotate_lowlevel_helper(a, ll_h, [s_R, s_ll_f, annmodel.SomePtr(A_repr.lowleveltype)])
    s = a.binding(ll_h_graph.getreturnvar())
    assert s.ll_ptrtype == A_repr.lowleveltype
    rt.specialize_more_blocks()

    from pypy.rpython.llinterp import LLInterpreter    
    interp = LLInterpreter(rt)

    c_f = r_f.convert_const(i.f)
    c_a = A_repr.convert_const(A(None))
    res = interp.eval_graph(ll_h_graph, [None, c_f, c_a])
    assert typeOf(res) == A_repr.lowleveltype

def test_function_or_none():
    def h(y):
        return y+84
    def g(y):
        return y+42
    def f(x, y):
        d = {1: g, 2:h}
        func = d.get(x, None)
        if func:
            return func(y)
        return -1
    res = interpret(f, [1, 100])
    assert res == 142
    res = interpret(f, [2, 100])
    assert res == 184
    res = interpret(f, [3, 100])
    assert res == -1

def test_pbc_getattr_conversion():
    fr1 = Freezing()
    fr2 = Freezing()
    fr3 = Freezing()
    fr1.value = 10
    fr2.value = 5
    fr3.value = 2.5
    def pick12(i):
        if i > 0:
            return fr1
        else:
            return fr2
    def pick23(i):
        if i > 5:
            return fr2
        else:
            return fr3
    def f(i):
        x = pick12(i)
        y = pick23(i)
        return x.value, y.value
    for i in [0, 5, 10]:
        res = interpret(f, [i])
        assert type(res.item0) is int   # precise
        assert type(res.item1) is float
        assert res.item0 == f(i)[0]
        assert res.item1 == f(i)[1]

def test_pbc_getattr_conversion_with_classes():
    class base: pass
    class fr1(base): pass
    class fr2(base): pass
    class fr3(base): pass
    fr1.value = 10
    fr2.value = 5
    fr3.value = 2.5
    def pick12(i):
        if i > 0:
            return fr1
        else:
            return fr2
    def pick23(i):
        if i > 5:
            return fr2
        else:
            return fr3
    def f(i):
        x = pick12(i)
        y = pick23(i)
        return x.value, y.value
    for i in [0, 5, 10]:
        res = interpret(f, [i])
        assert type(res.item0) is int   # precise
        assert type(res.item1) is float
        assert res.item0 == f(i)[0]
        assert res.item1 == f(i)[1]

def test_multiple_specialized_functions():
    def myadder(x, y):   # int,int->int or str,str->str
        return x+y
    def myfirst(x, y):   # int,int->int or str,str->str
        return x
    def mysecond(x, y):  # int,int->int or str,str->str
        return y
    myadder._annspecialcase_ = 'specialize:argtype(0)'
    myfirst._annspecialcase_ = 'specialize:argtype(0)'
    mysecond._annspecialcase_ = 'specialize:argtype(0)'
    def f(i):
        if i == 0:
            g = myfirst
        elif i == 1:
            g = mysecond
        else:
            g = myadder
        s = g("hel", "lo")
        n = g(40, 2)
        return len(s) * n
    for i in range(3):
        res = interpret(f, [i])
        assert res == f(i)

def test_specialized_method_of_frozen():
    class space:
        def __init__(self, tag):
            self.tag = tag
        def wrap(self, x):
            if isinstance(x, int):
                return self.tag + '< %d >' % x
            else:
                return self.tag + x
        wrap._annspecialcase_ = 'specialize:argtype(1)'
    space1 = space("tag1:")
    space2 = space("tag2:")
    def f(i):
        if i == 1:
            sp = space1
        else:
            sp = space2
        w1 = sp.wrap('hello')
        w2 = sp.wrap(42)
        return w1 + w2
    res = interpret(f, [1])
    assert ''.join(res.chars) == 'tag1:hellotag1:< 42 >'
    res = interpret(f, [0])
    assert ''.join(res.chars) == 'tag2:hellotag2:< 42 >'

def test_call_from_list():
    def f0(n): return n+200
    def f1(n): return n+192
    def f2(n): return n+46
    def f3(n): return n+2987
    def f4(n): return n+217
    lst = [f0, f1, f2, f3, f4]
    def f(i, n):
        return lst[i](n)
    for i in range(5):
        res = interpret(f, [i, 1000])
        assert res == f(i, 1000)

def test_precise_method_call_1():
    class A(object):
        def meth(self, x=5):
            return x+1
    class B(A):
        def meth(self, x=5):
            return x+2
    class C(A):
        pass
    def f(i, n):
        # call both A.meth and B.meth with an explicit argument
        if i > 0:
            x = A()
        else:
            x = B()
        result1 = x.meth(n)
        # now call A.meth only, using the default argument
        result2 = C().meth()
        return result1 * result2
    for i in [0, 1]:
        res = interpret(f, [i, 1234])
        assert res == f(i, 1234)

def test_precise_method_call_2():
    class A(object):
        def meth(self, x=5):
            return x+1
    class B(A):
        def meth(self, x=5):
            return x+2
    class C(A):
        def meth(self, x=5):
            return x+3
    def f(i, n):
        # call both A.meth and B.meth with an explicit argument
        if i > 0:
            x = A()
        else:
            x = B()
        result1 = x.meth(n)
        # now call A.meth and C.meth, using the default argument
        if i > 0:
            x = C()
        else:
            x = A()
        result2 = x.meth()
        return result1 * result2
    for i in [0, 1]:
        res = interpret(f, [i, 1234])
        assert res == f(i, 1234)


class TestLltype(BaseTestRPBC):

    ts = "lltype"

    def class_name(self, value):
        return "".join(value.super.typeptr.name)[:-1]

    def read_attr(self, value, attr_name):
        value = value._obj
        while value is not None:
            attr = getattr(value, "inst_" + attr_name, None)
            if attr is None:
                value = value._parentstructure()
            else:
                return attr
        raise AttributeError()

class TestOotype(BaseTestRPBC):

    ts = "ootype"

    def class_name(self, value):
        return typeOf(value)._name 

    def read_attr(self, value, attr):
        return getattr(value, "o" + attr)

