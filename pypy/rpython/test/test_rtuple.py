from pypy.translator.translator import TranslationContext
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.rtuple import *
from pypy.rpython.rint import signed_repr
from pypy.rpython.rbool import bool_repr
from pypy.rpython.test.test_llinterp import interpret 
import py

def test_rtuple():
    rtuple = TupleRepr(None, [signed_repr, bool_repr])
    assert rtuple.lowleveltype == Ptr(GcStruct('tuple2',
                                               ('item0', Signed),
                                               ('item1', Bool),
                                               ))

# ____________________________________________________________

def test_simple():
    def dummyfn(x):
        l = (10,x,30)
        return l[2]
    res = interpret(dummyfn,[4])
    assert res == 30

def test_len():
    def dummyfn(x):
        l = (5,x)
        return len(l)
    res = interpret(dummyfn, [4])
    assert res == 2

def test_return_tuple():
    def dummyfn(x, y):
        return (x<y, x>y)
    res = interpret(dummyfn, [4,5])
    assert res.item0 == True
    assert res.item1 == False

def test_tuple_concatenation():
    def f(n):
        tup = (1,n)
        tup1 = (3,)
        res = tup + tup1 + ()
        return res[0]*100 + res[1]*10 + res[2]
    res = interpret(f, [2])
    assert res == 123

def test_tuple_concatenation_mix():
    def f(n):
        tup = (1,n)
        tup1 = ('3',)
        res = tup + tup1
        return res[0]*100 + res[1]*10 + ord(res[2]) - ord('0')
    res = interpret(f, [2])
    assert res == 123

def test_constant_tuple_contains(): 
    def f(i): 
        t1 = (1, 2, 3, 4)
        return i in t1 
    res = interpret(f, [3], view=False, viewbefore=False) 
    assert res is True 
    res = interpret(f, [0])
    assert res is False 

def test_constant_tuple_contains2():
    def t1():
        return (1,2,3,4)
    def f(i): 
        return i in t1()
    res = interpret(f, [3], view=False, viewbefore=False) 
    assert res is True 
    res = interpret(f, [0])
    assert res is False 


def test_constant_unichar_tuple_contains():
    def f(i):
        return unichr(i) in (u'1', u'9')
    res = interpret(f, [49])
    assert res is True 
    res = interpret(f, [50])
    assert res is False 

def test_tuple_iterator_length1():
    def f(i):
        total = 0
        for x in (i,):
            total += x
        return total
    res = interpret(f, [93813])
    assert res == 93813

def test_conv():
    def t0():
        return (3, 2, None)
    def t1():
        return (7, 2, "xy")
    def f(i):
        if i == 1:
            return t1()
        else:
            return t0()

    res = interpret(f, [1])
    assert res.item0 == 7
    assert isinstance(typeOf(res.item2), Ptr) and ''.join(res.item2.chars) == "xy"
    res = interpret(f, [0])
    assert res.item0 == 3
    assert isinstance(typeOf(res.item2), Ptr) and not res.item2

def test_constant_tuples_shared():
    def g(n):
        x = (n, 42)    # constant (5, 42) detected by the annotator
        y = (5, 42)    # another one, built by the flow space
        z = x + ()     # yet another
        return id(x) == id(y) == id(z)
    def f():
        return g(5)
    res = interpret(f, [])
    assert res is True

def test_inst_tuple_getitem():
    class A:
        pass
    class B(A):
        pass

    def f(i):
        if i:
            x = (1, A())
        else:
            x = (1, B())
        return x[1]
    
    res = interpret(f, [0])
    assert ''.join(res.super.typeptr.name) == "B\00"
    
def test_inst_tuple_iter():
    class A:
        pass
    class B(A):
        pass

    def f(i):
        if i:
            x = (A(),)
        else:
            x = (B(),)
        l = []
        for y in x:
            l.append(y)
        return l[0]

    res = interpret(f, [0])
    assert ''.join(res.super.typeptr.name) == "B\00"

    
def test_inst_tuple_add_getitem():
    class A:
        pass
    class B(A):
        pass

    def f(i):
        x = (1, A())
        y = (2, B())
        if i:
            z = x + y
        else:
            z = y + x
        return z[1]
    
    res = interpret(f, [1])
    assert ''.join(res.super.typeptr.name) == "A\00"

    res = interpret(f, [0])
    assert ''.join(res.super.typeptr.name) == "B\00"
    

def test_type_erase():
    class A(object):
        pass
    class B(object):
        pass

    def f():
        return (A(), B()), (B(), A())

    t = TranslationContext()
    s = t.buildannotator().build_types(f, [])
    rtyper = t.buildrtyper()
    rtyper.specialize()

    s_AB_tup = s.items[0]
    s_BA_tup = s.items[1]
    
    r_AB_tup = rtyper.getrepr(s_AB_tup)
    r_BA_tup = rtyper.getrepr(s_AB_tup)

    assert r_AB_tup.lowleveltype == r_BA_tup.lowleveltype


def test_tuple_hash():
    def f(i, j):
        return hash((i, j))

    res1 = interpret(f, [12, 27])
    res2 = interpret(f, [27, 12])
    assert res1 != res2
