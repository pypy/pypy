from pypy.translator.translator import graphof
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.test import test_llinterp
from pypy.rpython.objectmodel import instantiate, we_are_translated
from pypy.rpython.lltypesystem import lltype
from pypy.tool import udir
from pypy.rpython.rarithmetic import r_uint, intmask
from pypy.annotation.builtin import *
from pypy.rpython.module.support import to_rstr
import py

def test_rbuiltin_list():
    def f(): 
        l=list((1,2,3))
        return l == [1,2,3]
    def g():
        l=list(('he','llo'))
        return l == ['he','llo']
    def r():
        l = ['he','llo']
        l1=list(l)
        return l == l1 and l is not l1
    result = interpret(f,[])
    assert result
    
    result = interpret(g,[])
    assert result
    
    result = interpret(r,[])
    assert result    
    
def test_int_min():
    def fn(i, j):
        return min(i,j)
    ev_fun = interpret(fn, [0, 0])
    assert interpret(fn, (1, 2)) == 1
    assert interpret(fn, (1, -1)) == -1
    assert interpret(fn, (2, 2)) == 2
    assert interpret(fn, (-1, -12)) == -12

def test_int_max():
    def fn(i, j):
        return max(i,j)
    assert interpret(fn, (1, 2)) == 2
    assert interpret(fn, (1, -1)) == 1
    assert interpret(fn, (2, 2)) == 2
    assert interpret(fn, (-1, -12)) == -1

def test_builtin_math_floor():
    import math
    def fn(f):
        return math.floor(f)
    import random 
    for i in range(5):
        rv = 1000 * float(i-10) #random.random()
        res = interpret(fn, [rv])
        assert fn(rv) == res 
        
def test_builtin_math_fmod():
    import math
    def fn(f,y):
        return math.fmod(f,y)

    for i in range(10):
        for j in range(10):
            rv = 1000 * float(i-10) 
            ry = 100 * float(i-10) +0.1
            assert fn(rv,ry) == interpret(fn, (rv, ry))

def enum_direct_calls(translator, func):
    blocks = []
    graph = graphof(translator, func)
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == 'direct_call':
                yield op

def test_os_getcwd():
    import os
    def fn():
        return os.getcwd()
    res = interpret(fn, []) 
    assert ''.join(res.chars) == fn()
        
def test_os_dup():
    import os
    def fn(fd):
        return os.dup(fd)
    res = interpret(fn, [0])
    try:
        os.close(res)
    except OSError:
        pass
    count = 0
    from pypy.rpython.module import ll_os
    for dir_call in enum_direct_calls(test_llinterp.typer.annotator.translator, fn):
        cfptr = dir_call.args[0]
        assert cfptr.value._obj._callable == ll_os.ll_os_dup
        count += 1
    assert count == 1

def test_os_open():
    tmpdir = str(udir.udir.join("os_open_test"))
    import os
    def wr_open(fname):
        return os.open(fname, os.O_WRONLY|os.O_CREAT, 0777)
    def f():
        return wr_open(tmpdir)
    res = interpret(f, [])
    os.close(res)
    count = 0
    from pypy.rpython.module import ll_os
    for dir_call in enum_direct_calls(test_llinterp.typer.annotator.translator, wr_open):
        cfptr = dir_call.args[0]
        assert cfptr.value._obj._callable == ll_os.ll_os_open
        count += 1
    assert count == 1

def test_os_path_exists():
    import os
    def f(fn):
        return os.path.exists(fn)
    filename = to_rstr(str(py.magic.autopath()))
    assert interpret(f, [filename]) == True
    assert interpret(f, [
        to_rstr("strange_filename_that_looks_improbable.sde")]) == False

def test_os_isdir():
    import os
    def f(fn):
        return os.path.isdir(fn)
    assert interpret(f, [to_rstr("/")]) == True
    assert interpret(f, [to_rstr(str(py.magic.autopath()))]) == False
    assert interpret(f, [to_rstr("another/unlikely/directory/name")]) == False
    

def test_pbc_isTrue():
    class C:
        def f(self):
            pass
        
    def g(obj):
        return bool(obj)
    def fn(neg):    
        c = C.f
        return g(c)
    assert interpret(fn, [True])
    def fn(neg):    
        c = None
        return g(c)
    assert not interpret(fn, [True]) 

def test_instantiate():
    class A:
        pass
    def f():
        return instantiate(A)
    res = interpret(f, [])
    assert res.super.typeptr.name[0] == 'A'

def test_instantiate_multiple():
    class A:
        pass
    class B(A):
        pass
    def f(i):
        if i == 1:
            cls = A
        else:
            cls = B
        return instantiate(cls)
    res = interpret(f, [1])
    assert res.super.typeptr.name[0] == 'A'
    res = interpret(f, [2])
    assert res.super.typeptr.name[0] == 'B'


def test_isinstance_obj():
    _1 = lltype.pyobjectptr(1)
    def f(x):
        return isinstance(x, int)
    res = interpret(f, [_1], someobjects=True)
    assert res is True
    _1_0 = lltype.pyobjectptr(1.0)
    res = interpret(f, [_1_0], someobjects=True)
    assert res is False


def test_const_isinstance():
    class B(object):
        pass
    def f():
        b = B()
        return isinstance(b, B)
    res = interpret(f, [])
    assert res is True

def test_isinstance():
    class A(object):
        pass
    class B(A):
        pass
    class C(A):
        pass
    def f(x, y):
        if x == 1:
            a = A()
        elif x == 2:
            a = B()
        else:
            a = C()
        if y == 1:
            res = isinstance(a, A)
            cls = A
        elif y == 2:
            res = isinstance(a, B)
            cls = B
        else:
            res = isinstance(a, C)
            cls = C
        return int(res) + 2 * isinstance(a, cls)
    for x in [1, 2, 3]:
        for y in [1, 2, 3]:
            res = interpret(f, [x, y])
            assert res == isinstance([A(), B(), C()][x-1], [A, B, C][y-1]) * 3

def test_isinstance_list():
    def f(i):
        if i == 0:
            l = []
        else:
            l = None
        return isinstance(l, list)
    res = interpret(f, [0])
    assert res is True
    res = interpret(f, [1])
    assert res is False    

def test_hasattr():
    class A(object):
        def __init__(self):
            self.x = 42
    def f(i):
        a = A()
        if i==0: return int(hasattr(A, '__init__'))
        if i==1: return int(hasattr(A, 'y'))
        if i==2: return int(hasattr(42, 'x'))
    for x, y in zip(range(3), (1, 0, 0)):
        res = interpret(f, [x])
        assert res._obj.value == y
    # hmm, would like to test against PyObj, is this the wrong place/way?

def test_we_are_translated():
    def f():
        return we_are_translated()
    res = interpret(f, [])
    assert res is True and f() is False

def test_method_join():
    # this is tuned to catch a specific bug:
    # a wrong rtyper_makekey() for BuiltinMethodRepr
    def f():
        lst1 = ['abc', 'def']
        s1 = ', '.join(lst1)
        lst2 = ['1', '2', '3']
        s2 = ''.join(lst2)
        return s1 + s2
    res = interpret(f, [])
    assert ''.join(list(res.chars)) == 'abc, def123'

def test_method_repr():
    def g(n):
        if n >= 0:
            return "egg"
        else:
            return "spam"
    def f(n):
        # this is designed for a specific bug: conversions between
        # BuiltinMethodRepr.  The append method of the list is passed
        # around, and g(-1) below causes a reflowing at the beginning
        # of the loop (but not inside the loop).  This situation creates
        # a newlist returning a SomeList() which '==' but 'is not' the
        # SomeList() inside the loop.
        x = len([ord(c) for c in g(1)])
        g(-1)
        return x
    res = interpret(f, [0])
    assert res == 3

def test_chr():
    def f(x=int):
        try:
            return chr(x)
        except ValueError:
            return '?'
    res = interpret(f, [65])
    assert res == 'A'
    res = interpret(f, [256])
    assert res == '?'
    res = interpret(f, [-1])
    assert res == '?'


def test_intmask():
    def f(x=r_uint):
        try:
            return intmask(x)
        except ValueError:
            return 0

    res = interpret(f, [r_uint(5)])
    assert type(res) is int and res == 5

def test_cast_primitive():
    from pypy.rpython.annlowlevel import LowLevelAnnotatorPolicy
    def llf(u):
        return lltype.cast_primitive(lltype.Signed, u)
    res = interpret(llf, [r_uint(-1)], policy=LowLevelAnnotatorPolicy())
    assert res == -1
    res = interpret(llf, ['x'], policy=LowLevelAnnotatorPolicy())
    assert res == ord('x')
    def llf(v):
        return lltype.cast_primitive(lltype.Unsigned, v)
    res = interpret(llf, [-1], policy=LowLevelAnnotatorPolicy())
    assert res == r_uint(-1)
    res = interpret(llf, [u'x'], policy=LowLevelAnnotatorPolicy())
    assert res == ord(u'x')
    res = interpret(llf, [1.0], policy=LowLevelAnnotatorPolicy())
    assert res == r_uint(1)
    def llf(v):
        return lltype.cast_primitive(lltype.Char, v)
    res = interpret(llf, [ord('x')], policy=LowLevelAnnotatorPolicy())
    assert res == 'x'
    def llf(v):
        return lltype.cast_primitive(lltype.UniChar, v)
    res = interpret(llf, [ord('x')], policy=LowLevelAnnotatorPolicy())
    assert res == u'x'

def test_cast_subarray_pointer():
    from pypy.rpython.lltypesystem.lltype import malloc, GcArray, Signed
    from pypy.rpython.lltypesystem.lltype import FixedSizeArray, Ptr
    for a in [malloc(GcArray(Signed), 5),
              malloc(FixedSizeArray(Signed, 5), immortal=True)]:
        a[0] = 0
        a[1] = 10
        a[2] = 20
        a[3] = 30
        a[4] = 40
        BOX = Ptr(FixedSizeArray(Signed, 2))
        b01 = lltype.cast_subarray_pointer(BOX, a, 0)
        b12 = lltype.cast_subarray_pointer(BOX, a, 1)
        b23 = lltype.cast_subarray_pointer(BOX, a, 2)
        b34 = lltype.cast_subarray_pointer(BOX, a, 3)
        def llf(n):
            saved = a[n]
            a[n] = 1000
            try:
                return b01[0] + b12[0] + b23[1] + b34[1]
            finally:
                a[n] = saved

        res = interpret(llf, [0])
        assert res == 1000 + 10 + 30 + 40
        res = interpret(llf, [1])
        assert res == 0 + 1000 + 30 + 40
        res = interpret(llf, [2])
        assert res == 0 + 10 + 30 + 40
        res = interpret(llf, [3])
        assert res == 0 + 10 + 1000 + 40
        res = interpret(llf, [4])
        assert res == 0 + 10 + 30 + 1000

def test_cast_structfield_pointer():
    S = lltype.GcStruct('S', ('x', lltype.Signed), ('y', lltype.Signed))
    SUBARRAY = lltype.FixedSizeArray(lltype.Signed, 1)
    P = lltype.Ptr(SUBARRAY)
    def llf(n):
        s = lltype.malloc(S)
        a = lltype.cast_structfield_pointer(P, s, 'y')
        a[0] = n
        return s.y

    res = interpret(llf, [34])
    assert res == 34
