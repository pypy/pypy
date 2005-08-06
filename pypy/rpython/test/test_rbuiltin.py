from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.test import test_llinterp
from pypy.rpython.objectmodel import instantiate, we_are_translated
from pypy.rpython import lltype
from pypy.objspace.flow import model as flowmodel
from pypy.tool import udir

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
    graph = translator.getflowgraph(func)
    def visit(block):
        if isinstance(block, flowmodel.Block):
            blocks.append(block)
    flowmodel.traverse(visit, graph)
    for block in blocks:
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
