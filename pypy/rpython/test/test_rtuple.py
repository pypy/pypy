from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.rtuple import *
from pypy.rpython.rint import signed_repr
from pypy.rpython.rbool import bool_repr
from pypy.rpython.test.test_llinterp import interpret 
import py

def test_rtuple():
    rtuple = TupleRepr([signed_repr, bool_repr])
    assert rtuple.lowleveltype == Ptr(GcStruct('tuple2',
                                               ('item0', Signed),
                                               ('item1', Bool),
                                               ))

# ____________________________________________________________

def rtype(fn, argtypes=[]):
    t = Translator(fn)
    t.annotate(argtypes)
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()
    return t


def test_simple():
    def dummyfn(x):
        l = (10,x,30)
        return l[2]
    rtype(dummyfn, [int])

def test_len():
    def dummyfn(x):
        l = (5,x)
        return len(l)
    rtype(dummyfn, [int])

##def test_iterate():
##    def dummyfn():
##        total = 0
##        for x in (1,3,5,7,9):
##            total += x
##        return total
##    rtype(dummyfn)

def test_return_tuple():
    def dummyfn(x, y):
        return (x<y, x>y)
    rtype(dummyfn, [int, int])

def test_tuple_concatenation():
    def f():
        tup = (1,2)
        tup1 = (3,)
        res = tup + tup1 + ()
        return res[0]*100 + res[1]*10 + res[2]
    res = interpret(f, []) 
    assert res == 123

def test_tuple_concatenation_mix():
    def f():
        tup = (1,2)
        tup1 = ('3',)
        res = tup + tup1
        return res[0]*100 + res[1]*10 + ord(res[2]) - ord('0')
    res = interpret(f, []) 
    assert res == 123

def test_constant_tuple_contains(): 
    def f(i): 
        t1 = (1, 2, 3, 4)
        return i in t1 
    res = interpret(f, [3], view=False, viewbefore=False) 
    assert res is True 
    res = interpret(f, [0])
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
