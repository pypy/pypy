from pypy.translator.translator import graphof
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.test import test_llinterp
from pypy.rpython.objectmodel import instantiate, we_are_translated
from pypy.rpython.lltypesystem import lltype
from pypy.tool import udir
from pypy.rpython.rarithmetic import r_uint, intmask
from pypy.annotation.builtin import *
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
import py


def enum_direct_calls(translator, func):
    blocks = []
    graph = graphof(translator, func)
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == 'direct_call':
                yield op

    


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


class BaseTestExtfunc(BaseRtypingTest):

    def test_rbuiltin_list(self):
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
        result = self.interpret(f,[])
        assert result

        result = self.interpret(g,[])
        assert result

        result = self.interpret(r,[])
        assert result    

    def test_int_min(self):
        def fn(i, j):
            return min(i,j)
        ev_fun = self.interpret(fn, [0, 0])
        assert self.interpret(fn, (1, 2)) == 1
        assert self.interpret(fn, (1, -1)) == -1
        assert self.interpret(fn, (2, 2)) == 2
        assert self.interpret(fn, (-1, -12)) == -12

    def test_int_max(self):
        def fn(i, j):
            return max(i,j)
        assert self.interpret(fn, (1, 2)) == 2
        assert self.interpret(fn, (1, -1)) == 1
        assert self.interpret(fn, (2, 2)) == 2
        assert self.interpret(fn, (-1, -12)) == -1

    def test_builtin_math_floor(self):
        import math
        def fn(f):
            return math.floor(f)
        import random 
        for i in range(5):
            rv = 1000 * float(i-10) #random.random()
            res = self.interpret(fn, [rv])
            assert fn(rv) == res 

    def test_builtin_math_fmod(self):
        import math
        def fn(f,y):
            return math.fmod(f,y)

        for i in range(10):
            for j in range(10):
                rv = 1000 * float(i-10) 
                ry = 100 * float(i-10) +0.1
                assert fn(rv,ry) == self.interpret(fn, (rv, ry))


    def test_os_getcwd(self):
        import os
        def fn():
            return os.getcwd()
        res = self.interpret(fn, []) 
        assert self.ll_to_string(res) == fn()
        
    def test_os_write(self):
        tmpdir = str(udir.udir.join("os_write_test"))
        import os
        def wr_open(fname):
            fd = os.open(fname, os.O_WRONLY|os.O_CREAT, 0777)
            os.write(fd, "hello world")
            return fd
        def f():
            return wr_open(tmpdir)
        res = self.interpret(f, [])
        os.close(res)
        hello = open(tmpdir).read()
        assert hello == "hello world"

    def test_os_dup(self):
        import os
        def fn(fd):
            return os.dup(fd)
        res = self.interpret(fn, [0])
        try:
            os.close(res)
        except OSError:
            pass
        count = 0
        for dir_call in enum_direct_calls(test_llinterp.typer.annotator.translator, fn):
            cfptr = dir_call.args[0]
            assert self.get_callable(cfptr.value) == self.ll_os.Implementation.ll_os_dup.im_func
            count += 1
        assert count == 1

    def test_os_open(self):
        tmpdir = str(udir.udir.join("os_open_test"))
        import os
        def wr_open(fname):
            return os.open(fname, os.O_WRONLY|os.O_CREAT, 0777)
        def f():
            return wr_open(tmpdir)
        res = self.interpret(f, [])
        os.close(res)
        count = 0
        for dir_call in enum_direct_calls(test_llinterp.typer.annotator.translator, wr_open):
            cfptr = dir_call.args[0]
            assert self.get_callable(cfptr.value) == self.ll_os.Implementation.ll_os_open.im_func
            count += 1
        assert count == 1

    def test_os_path_exists(self):
        import os
        def f(fn):
            return os.path.exists(fn)
        filename = self.string_to_ll(str(py.magic.autopath()))
        assert self.interpret(f, [filename]) == True
        assert self.interpret(f, [
            self.string_to_ll("strange_filename_that_looks_improbable.sde")]) == False

    def test_os_isdir(self):
        import os
        def f(fn):
            return os.path.isdir(fn)
        assert self.interpret(f, [self.string_to_ll("/")]) == True
        assert self.interpret(f, [self.string_to_ll(str(py.magic.autopath()))]) == False
        assert self.interpret(f, [self.string_to_ll("another/unlikely/directory/name")]) == False


class TestLLtype(BaseTestExtfunc, LLRtypeMixin):
    from pypy.rpython.lltypesystem.module import ll_os
    
class TestOOtype(BaseTestExtfunc, OORtypeMixin):
    from pypy.rpython.ootypesystem.module import ll_os
