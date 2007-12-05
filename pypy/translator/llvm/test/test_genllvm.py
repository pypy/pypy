from __future__ import division

import sys

import py
from pypy.rlib.rarithmetic import r_uint
from pypy.rpython.lltypesystem import lltype

from pypy.translator.llvm.test.runtest import *

def test_return1():
    def simple1():
        return 1
    f = compile_function(simple1, [])
    assert f() == 1

def test_simple_function_pointer(): 
    def f1(x): 
        return x + 1
    def f2(x): 
        return x + 2

    l = [f1, f2]

    def pointersimple(i): 
        return l[i](i)

    f = compile_function(pointersimple, [int])
    assert f(0) == pointersimple(0)
    assert f(1) == pointersimple(1)

def test_invoke_function_pointer(): 
    def f1(x): 
        return x + 1
    def f2(x): 
        return x + 2

    l = [f1, f2]

    def invokepointer(i): 
        try:
            return l[i](i)
        except:
            return 123

    f = compile_function(invokepointer, [int])
    assert f(0) == invokepointer(0)
    assert f(1) == invokepointer(1)

def test_invoke_function_pointer2(): 
    def f1(x):
        if x>0:
            raise Exception("bla")
        return 10
    def f2(x):
        return 5

    l = [f1, f2]

    def invokepointer(i,j): 
        try:
            return l[i](i)
        except:
            return 123

    f = compile_function(invokepointer, [int, int])
    assert f(0, 0) == invokepointer(0, 0)
    assert f(0, 1) == invokepointer(0, 1)
    assert f(1, 0) == invokepointer(1, 0)
    assert f(1, 1) == invokepointer(1, 1)

def test_simple_branching():
    def simple5(b):
        if b:
            x = 12
        else:
            x = 13
        return x
    f = compile_function(simple5, [bool])
    assert f(True) == 12
    assert f(False) == 13

def test_int_ops():
    def ops(i):
        x = 0
        x += i < i
        x += i <= i
        x += i == i
        x += i != i
        x += i >= i
        x += i > i
        x += x % i
        x += i + 1 * i // i - 1
        return x
    f = compile_function(ops, [int])
    assert f(1) == ops(1)
    assert f(2) == ops(2)
    
def test_uint_ops():
    def ops(i):
        x = 0
        x += i < i
        x += i <= i
        x += i == i
        x += i != i
        x += i >= i
        x += i > i
        x += x % i
        x += i + 1 * i // i - 1
        return x
    f = compile_function(ops, [r_uint])
    assert f(1) == ops(1)
    assert f(2) == ops(2)

def test_float_ops():
    def ops(flt):
        x = 0
        x += flt < flt
        x += flt <= flt
        x += flt == flt
        x += flt != flt
        x += flt >= flt
        x += flt > flt
        x += int(flt + 1 * flt / flt - 1)
        return x 
    f = compile_function(ops, [float])
    assert f(1) == ops(1)
    assert f(2) == ops(2)

def test_while_loop():
    def factorial(i):
        r = 1
        while i>1:
            r *= i
            i -= 1
        return r
    f = compile_function(factorial, [int])
    assert factorial(4) == 24
    assert factorial(5) == 120
    f = compile_function(factorial, [float])
    assert factorial(4.) == 24.
    assert factorial(5.) == 120.

def test_return_void():
    def return_void(i):
        return None
    def call_return_void(i):
        return_void(i)
        return 1
    f = compile_function(call_return_void, [int])
    assert f(10) == 1

def test_break_while_loop():
    def factorial(i):
        r = 1
        while 1:
            if i<=1:
                break
            r *= i
            i -= 1
        return r
    f = compile_function(factorial, [int])
    assert factorial(4) == 24
    assert factorial(5) == 120

def test_primitive_is_true():
    def var_is_true(v):
        return bool(v)
    f = compile_function(var_is_true, [int])
    assert f(256)
    assert not f(0)
    f = compile_function(var_is_true, [r_uint])
    assert f(r_uint(256))
    assert not f(r_uint(0))
    f = compile_function(var_is_true, [float])
    assert f(256.0)
    assert not f(0.0)

def test_function_call():
    def callee():
        return 1
    def caller():
        return 3 + callee()
    f = compile_function(caller, [])
    assert f() == 4

def test_recursive_call():
    def call_ackermann(n, m):
        return ackermann(n, m)
    def ackermann(n, m):
        if n == 0:
            return m + 1
        if m == 0:
            return ackermann(n - 1, 1)
        return ackermann(n - 1, ackermann(n, m - 1))
    f = compile_function(call_ackermann, [int, int])
    assert f(0, 2) == 3
    
def test_tuple_getitem(): 
    def tuple_getitem(i): 
        l = (4,5,i)
        return l[1]
    f = compile_function(tuple_getitem, [int])
    assert f(1) == tuple_getitem(1)

def test_nested_tuple():
    def nested_tuple(i): 
        l = (1,(1,2,i),i)
        return l[1][2]
    f = compile_function(nested_tuple, [int])
    assert f(4) == 4

def test_prebuilt_tuples():
    t1 = (1,2,3,4)
    t2 = (5,6,7,8)
    def callee_tuple(t):
        return t[0]
    def caller_tuple(i):
        if i:
            return callee_tuple(t1) + i
        else:
            return callee_tuple(t2) + i
    f = compile_function(caller_tuple, [int])
    assert f(0) == 5
    assert f(1) == 2

def test_pbc_fns(): 
    def f2(x):
         return x+1
    def f3(x):
         return x+2
    def g(y):
        if y < 0:
            f = f2
        else:
            f = f3
        return f(y+3)
    f = compile_function(g, [int])
    assert f(-1) == 3
    assert f(0) == 5

def test_simple_chars():
     def char_constant2(s):
         s = s + s + s
         return len(s + '.')
     def char_constant():
         return char_constant2("kk")    
     f = compile_function(char_constant, [])
     assert f() == 7

def test_list_getitem(): 
    def list_getitem(i): 
        l = [1,2,i+1]
        return l[i]
    f = compile_function(list_getitem, [int])
    assert f(0) == 1
    assert f(1) == 2
    assert f(2) == 3

def test_list_list_getitem(): 
    def list_list_getitem(): 
        l = [[1]]
        return l[0][0]
    f = compile_function(list_list_getitem, [])
    assert f() == 1

def test_list_getitem_pbc(): 
    l = [1,2]
    def list_getitem_pbc(i): 
        return l[i]
    f = compile_function(list_getitem_pbc, [int])
    assert f(0) == 1
    assert f(1) == 2
    
def test_list_list_getitem_pbc(): 
    l = [[0, 1], [0, 1]]
    def list_list_getitem_pbc(i): 
        return l[i][i]
    f = compile_function(list_list_getitem_pbc, [int])
    assert f(0) == 0
    assert f(1) == 1

def test_list_basic_ops(): 
    def list_basic_ops(i, j): 
        l = [1,2,3]
        l.insert(0, 42)
        del l[1]
        l.append(i)
        listlen = len(l)
        l.extend(l) 
        del l[listlen:]
        l += [5,6]
        l[1] = i
        return l[j]
    f = compile_function(list_basic_ops, [int, int])
    for i in range(6): 
        for j in range(6): 
            assert f(i,j) == list_basic_ops(i,j)

def test_string_simple(): 
    def string_simple(i): 
        return ord(str(i))
    f = compile_function(string_simple, [int])
    assert f(0) 
    
def test_string_simple_ops(): 
    def string_simple_ops(i): 
        res = 0
        s = str(i)
        s2 = s + s + s + s
        s3 = s + s + s + s
        res += s != s2
        res += s2 == s3
        res += ord(s)
        return res
    f = compile_function(string_simple_ops, [int])
    assert f(5) == ord('5') + 2
        
def test_string_getitem1():
    l = "Hello, World"
    def string_getitem1(i): 
        return ord(l[i])
    f = compile_function(string_getitem1, [int])
    assert f(0) == ord("H")

def test_string_getitem2():
    def string_test(i): 
        l = "Hello, World"
        return ord(l[i])
    f = compile_function(string_test, [int])
    assert f(0) == ord("H")

def test_list_of_string(): 
    a = ["hello", "world"]
    def string_simple(i, j, k, l):
        s = a[i][j] + a[k][l]
        return ord(s[0]) + ord(s[1])        
    f = compile_function(string_simple, [int, int, int, int])
    assert f(0, 0, 1, 4) == ord("h") + ord("d")

def test_attrs_class():
    class MyBase:
        pass
    def attrs_class(a):
        obj = MyBase()
        obj.z = a
        return obj.z * 4
    f = compile_function(attrs_class, [int])
    assert f(4) == 16

def test_attrs_class_pbc():
    class MyBase:
        pass
    obj = MyBase()
    obj.z = 4
    def attrs_class_pbc():
        return obj.z * 4
    f = compile_function(attrs_class_pbc, [])
    assert f() == 16

def test_method_call():
    class MyBase:
        def m(self): return self.z
    obj = MyBase()
    obj.z = 4
    def method_call():
        return obj.m()
    f = compile_function(method_call, [])
    assert f() == 4

def test_dict_creation(): 
    d = {'hello' : 23,
         'world' : 21}
    l = ["hello", "world"]
    def createdict(i, j):
        return d[l[i]] + d[l[j]]
    assert createdict(0,1) == 44
    f = compile_function(createdict, [int, int])
    assert f(0,1) == createdict(0,1)

def test_closure(): 
    class A:
        def set(self, x):
            self.x = x
        def get(self):
            return self.x
    class B(A):
        def get(self):
            return A.get(self) * 2
    a = A()
    b = B()
    def createfn(y):
        z = 42
        def fn(x):
            return x + y + z + a.get() + b.get()
        f2 = lambda: A.get(b)
        def getfn(x):
            if x % 2:
                f = A.get
            else:
                f = B.get
            return f
        def proxy(s):
            f1 = s.get
            t = 0
            for ii in range(5):
                f3 = getfn(ii)
                t += f1()
                t += f2()
                t += f3(s)
            return t
        setattr(B, "f2", proxy)
        return fn
    fn = createfn(10)
    def testf(x):
        a.set(10)        
        b.set(25)        
        return fn(x) + b.get() + b.f2()
    f = compile_function(testf, [int])
    assert f(1) == testf(1)
    assert f(2) == testf(2)

def test_broken_after_transform():
    class A:
        pass
    a = A()
    a.count = 0
    
    def drop(n):
        loops = 0
        while n > 0:
            n -= 1
            a.count += 1

    def rundrop(n):
        drop(n)
        return a.count

    f = compile_function(rundrop, [int])
    assert f(42) == 42
    f = compile_function(rundrop, [int])
    assert f(0) == 0
    

def test_switch_no_default():
    from pypy.objspace.flow.model import FunctionGraph, Block, Constant, Link
    from pypy.rpython.lltypesystem.lltype import FuncType, Signed, functionptr
    from pypy.translator.unsimplify import varoftype
    block = Block([varoftype(Signed)])
    block.exitswitch = block.inputargs[0]
    graph = FunctionGraph("t", block, varoftype(Signed))
    links = []
    for i in range(10):
        links.append(Link([Constant(i*i, Signed)], graph.returnblock, i))
        links[-1].llexitcase = i
    block.closeblock(*links)
    fptr = functionptr(FuncType([Signed], Signed), "t", graph=graph)
    def func(x):
        return fptr(x)
    f = compile_function(func, [int])
    res = f(4)
    assert res == 16

def test_call_boehm_gc_alloc():
    from pypy.rpython.lltypesystem import llmemory, lltype
    from pypy.rpython.lltypesystem.lloperation import llop
    def f(s):
        a = llop.call_boehm_gc_alloc(llmemory.Address, 100)
        a.signed[0] = s
        a.signed[1] = s+2
        return a.signed[0]*a.signed[1]
    f = compile_function(f, [int])
    res = f(4)
    assert res == 4*(4+2)


def func_with_dup_name():
    return 1

foo_func_with_dup_name = func_with_dup_name

def test_dup_func():
    def func_with_dup_name():
        return 2
    def func_with_dup_name_1():
        return 3
    def call_func(x):
        if x > 10:
            return foo_func_with_dup_name()
        elif x > 5:
            return func_with_dup_name_1()
        elif x > 0:
            return func_with_dup_name()
        return 0
    f = compile_function(call_func, [int])
    assert f(1) == 2
    assert f(6) == 3
    assert f(11) == 1


def test__del__():
    from pypy.rpython.lltypesystem.lloperation import llop
    class State:
        pass
    s = State()
    class A(object):
        def __del__(self):
            s.a_dels += 1
    class B(A):
        def __del__(self):
            s.b_dels += 1
    class C(A):
        pass
    def f():
        s.a_dels = 0
        s.b_dels = 0
        A()
        B()
        C()
        A()
        B()
        C()
        llop.gc__collect(lltype.Void)
        return s.a_dels * 10 + s.b_dels
    fn = compile_function(f, [])
    # we can't demand that boehm has collected all of the objects,
    # even with the gc__collect call.  calling the compiled
    # function twice seems to help, though.
    res = 0
    res += fn()
    res += fn()
    
    # if res is still 0, then we haven't tested anything so fail.
    assert 0 < res <= 84 
 
def test_debug():
    # just tests code runs
    def simple():
        return 42
    f = compile_function(simple, [], debug=True)
    assert f() == 42
