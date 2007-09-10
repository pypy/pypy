from pypy.translator.translator import graphof
from pypy.rpython.test import test_llinterp
from pypy.rlib.objectmodel import instantiate, we_are_translated
from pypy.rpython.lltypesystem import lltype
from pypy.tool import udir
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.annotation.builtin import *
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rpython.rctypes.rcarithmetic import CShort
from pypy.rpython import extfunc
import py


def enum_direct_calls(translator, func):
    blocks = []
    graph = graphof(translator, func)
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == 'direct_call':
                yield op


class BaseTestRbuiltin(BaseRtypingTest):

    def test_method_join(self):
        # this is tuned to catch a specific bug:
        # a wrong rtyper_makekey() for BuiltinMethodRepr
        def f():
            lst1 = ['abc', 'def']
            s1 = ', '.join(lst1)
            lst2 = ['1', '2', '3']
            s2 = ''.join(lst2)
            return s1 + s2
        res = self.interpret(f, [])
        assert self.ll_to_string(res) == 'abc, def123'

    def test_method_repr(self):
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
        res = self.interpret(f, [0])
        assert res == 3

    def test_chr(self):
        def f(x=int):
            try:
                return chr(x)
            except ValueError:
                return '?'
        res = self.interpret(f, [65])
        assert res == 'A'
        res = self.interpret(f, [256])
        assert res == '?'
        res = self.interpret(f, [-1])
        assert res == '?'

    def test_intmask(self):
        def f(x=r_uint):
            try:
                return intmask(x)
            except ValueError:
                return 0

        res = self.interpret(f, [r_uint(5)])
        assert type(res) is int and res == 5

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

    def test_float_min(self):
        def fn(i, j):
            return min(i, j)
        assert self.interpret(fn, (1.9, 2.)) == 1.9
        assert self.interpret(fn, (1.5, -1.4)) == -1.4

    def test_float_int_min(self):
        def fn(i, j):
            return min(i, j)
        assert self.interpret(fn, (1.9, 2)) == 1.9
        assert self.interpret(fn, (1.5, -1)) == -1

    def test_float_max(self):
        def fn(i, j):
            return max(i,j)
        assert self.interpret(fn, (1.0, 2.)) == 2
        assert self.interpret(fn, (1.1, -1)) == 1.1

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
                assert self.float_eq(fn(rv,ry), self.interpret(fn, (rv, ry)))

    def test_builtin_math_frexp(self):
        import math
        def fn(f):
            return math.frexp(f)
        res = self.interpret(fn, [10/3.0])
        mantissa, exponent = math.frexp(10/3.0)        
        assert self.float_eq(res.item0, mantissa) and self.float_eq(res.item1, exponent)

    def test_builtin_math_modf(self):
        import math
        def fn(f):
            return math.modf(f)
        res = self.interpret(fn, [10/3.0])
        intpart, fracpart = math.modf(10/3.0)
        assert self.float_eq(res.item0, intpart) and self.float_eq(res.item1, fracpart)

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

    def test_os_write_single_char(self):
        tmpdir = str(udir.udir.join("os_write_test_char"))
        import os
        def wr_open(fname):
            fd = os.open(fname, os.O_WRONLY|os.O_CREAT, 0777)
            os.write(fd, "x")
            return fd
        def f():
            return wr_open(tmpdir)
        res = self.interpret(f, [])
        os.close(res)
        hello = open(tmpdir).read()
        assert hello == "x"

    def test_os_read(self):
        import os
        tmpfile = str(udir.udir.join("os_read_test"))
        f = file(tmpfile, 'w')
        f.write('hello world')
        f.close()
        def f():
            fd = os.open(tmpfile, os.O_RDONLY, 0777)
            return os.read(fd, 4096)
        res = self.interpret(f, [])
        assert self.ll_to_string(res) == 'hello world'

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
            assert self.get_callable(cfptr.value).__name__.startswith('dup')
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
            assert self.get_callable(cfptr.value).__name__.startswith('os_open')
            count += 1
        assert count == 1

    def test_os_path_exists(self):
        self._skip_llinterpreter("os.stat()")
        import os
        def f(fn):
            return os.path.exists(fn)
        filename = self.string_to_ll(str(py.magic.autopath()))
        assert self.interpret(f, [filename]) == True
        assert self.interpret(f, [
            self.string_to_ll("strange_filename_that_looks_improbable.sde")]) == False

    def test_os_isdir(self):
        self._skip_llinterpreter("os.stat()")
        import os
        def f(fn):
            return os.path.isdir(fn)
        assert self.interpret(f, [self.string_to_ll("/")]) == True
        assert self.interpret(f, [self.string_to_ll(str(py.magic.autopath()))]) == False
        assert self.interpret(f, [self.string_to_ll("another/unlikely/directory/name")]) == False

    def test_pbc_isTrue(self):
        class C:
            def f(self):
                pass

        def g(obj):
            return bool(obj)
        def fn(neg):    
            c = C.f
            return g(c)
        assert self.interpret(fn, [True])
        def fn(neg):    
            c = None
            return g(c)
        assert not self.interpret(fn, [True]) 

    def test_const_isinstance(self):
        class B(object):
            pass
        def f():
            b = B()
            return isinstance(b, B)
        res = self.interpret(f, [])
        assert res is True

    def test_isinstance(self):
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
                res = self.interpret(f, [x, y])
                assert res == isinstance([A(), B(), C()][x-1], [A, B, C][y-1]) * 3

    def test_isinstance_list(self):
        def f(i):
            if i == 0:
                l = []
            else:
                l = None
            return isinstance(l, list)
        res = self.interpret(f, [0])
        assert res is True
        res = self.interpret(f, [1])
        assert res is False

    def test_instantiate(self):
        class A:
            pass
        def f():
            return instantiate(A)
        res = self.interpret(f, [])
        assert self.class_name(res) == 'A'

    def test_instantiate_multiple(self):
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
        res = self.interpret(f, [1])
        assert self.class_name(res) == 'A'
        res = self.interpret(f, [2])
        assert self.class_name(res) == 'B'

    def test_os_path_join(self):
        self._skip_llinterpreter("os path oofakeimpl", skipLL=False)
        import os.path
        def fn(a, b):
            return os.path.join(a, b)
        res = self.ll_to_string(self.interpret(fn, ['a', 'b']))
        assert res == os.path.join('a', 'b')

    def test_exceptions(self):
        def fn(a):
            try:
                a += int(str(int(a)))
                a += int(int(a > 5))
            finally:
                return a
        res = self.interpret(fn, [3.25])
        assert res == 7.25

class TestLLtype(BaseTestRbuiltin, LLRtypeMixin):

    def test_isinstance_obj(self):
        _1 = lltype.pyobjectptr(1)
        def f(x):
            return isinstance(x, int)
        res = self.interpret(f, [_1], someobjects=True)
        assert res is True
        _1_0 = lltype.pyobjectptr(1.0)
        res = self.interpret(f, [_1_0], someobjects=True)
        assert res is False

    def test_hasattr(self):
        class A(object):
            def __init__(self):
                self.x = 42
        def f(i):
            a = A()
            if i==0: return int(hasattr(A, '__init__'))
            if i==1: return int(hasattr(A, 'y'))
            if i==2: return int(hasattr(42, 'x'))
        for x, y in zip(range(3), (1, 0, 0)):
            res = self.interpret(f, [x], someobjects=True)
            assert res._obj.value == y
        # hmm, would like to test against PyObj, is this the wrong place/way?

    def test_cast_primitive(self):
        from pypy.rpython.annlowlevel import LowLevelAnnotatorPolicy
        def llf(u):
            return lltype.cast_primitive(lltype.Signed, u)
        res = self.interpret(llf, [r_uint(-1)], policy=LowLevelAnnotatorPolicy())
        assert res == -1
        res = self.interpret(llf, ['x'], policy=LowLevelAnnotatorPolicy())
        assert res == ord('x')
        def llf(v):
            return lltype.cast_primitive(lltype.Unsigned, v)
        res = self.interpret(llf, [-1], policy=LowLevelAnnotatorPolicy())
        assert res == r_uint(-1)
        res = self.interpret(llf, [u'x'], policy=LowLevelAnnotatorPolicy())
        assert res == ord(u'x')
        res = self.interpret(llf, [1.0], policy=LowLevelAnnotatorPolicy())
        assert res == r_uint(1)
        def llf(v):
            return lltype.cast_primitive(lltype.Char, v)
        res = self.interpret(llf, [ord('x')], policy=LowLevelAnnotatorPolicy())
        assert res == 'x'
        def llf(v):
            return lltype.cast_primitive(lltype.UniChar, v)
        res = self.interpret(llf, [ord('x')], policy=LowLevelAnnotatorPolicy())
        assert res == u'x'
        def llf(v):
            return lltype.cast_primitive(CShort, v)
        res = self.interpret(llf, [123], policy=LowLevelAnnotatorPolicy())
        assert res == 123


    
class TestOOtype(BaseTestRbuiltin, OORtypeMixin):

    def test_instantiate_meta(self):
        class A:
            pass
        def f():
            return instantiate(A)
        res = self.interpret(f, [])
        assert res.meta # check that it's not null

    def test_instantiate_multiple_meta(self):
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
        res = self.interpret(f, [1])
        assert res.meta # check that it's not null
