"""
Test external function calls.
"""

import py
import sys
import pypy.rpython.rctypes.implementation
from pypy.rpython.rctypes.rmodel import unsafe_getfield
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.test.test_llinterp import interpret
from pypy.translator.c.test.test_genc import compile
from pypy import conftest
from pypy.rpython.lltypesystem.rstr import string_repr
from pypy.rpython.lltypesystem import lltype, llmemory

from ctypes import cdll, pythonapi, PyDLL, _FUNCFLAG_PYTHONAPI
from ctypes import c_int, c_long, c_char_p, c_void_p, c_char
from ctypes import create_string_buffer, cast
from ctypes import POINTER, py_object, byref, Structure
from pypy.rpython.rctypes.tool import util      # ctypes.util from 0.9.9.6

# __________ the standard C library __________

if sys.platform == 'win32':
    mylib = cdll.LoadLibrary('msvcrt.dll')
else:
    clib  = util.find_library('c')
    mylib = cdll.LoadLibrary(clib)

# ____________________________________________

labs = mylib.labs
labs.restype = c_long
labs.argtypes = [c_long]
def ll_labs(n):
    return abs(n)
labs.llinterp_friendly_version = ll_labs

atoi = mylib.atoi
atoi.restype = c_int
atoi.argtypes = [c_char_p]
def ll_atoi(p):
    "Very approximative ll implementation of atoi(), for testing"
    i = result = 0
    while '0' <= p[i] <= '9':
        result = result * 10 + ord(p[i]) - ord('0')
        i += 1
    return result
atoi.llinterp_friendly_version = ll_atoi

atol = mylib.atol
atol.restype = c_long
atol.argtypes = [c_char_p]
atol.llinterp_friendly_version = ll_atoi

strlen = mylib.strlen
strlen.restype = c_long
strlen.argtypes = [c_char_p]

time_ = mylib.time
time_.restype = c_long    # should rather use ctypes_platform.getsimpletype()
time_.argtypes = [POINTER(c_long)]

ctime = mylib.ctime
ctime.restype = c_char_p
#ctimes.argtypes: omitted for this test

##IntIntCallback = CALLBACK_FUNCTYPE(c_int, c_int)
##def mycallback(n):
##    return n+3
##callback = IntIntCallback(mycallback)

##PyIntIntCallback = CALLBACK_FUNCTYPE(c_int, c_int, callconv=PyDLL)
##pycallback = PyIntIntCallback(mycallback)

def ll_memcpy(dst, src, length):
    C_ARRAY = lltype.Ptr(lltype.FixedSizeArray(lltype.Char, 1))
    c_src = llmemory.cast_adr_to_ptr(src, C_ARRAY)
    c_dst = llmemory.cast_adr_to_ptr(dst, C_ARRAY)
    for i in range(length):
        c_dst[i] = c_src[i]
    return dst

memcpy = mylib.memcpy
memcpy.argtypes = [c_void_p, c_void_p, c_long]
memcpy.restype = c_void_p
memcpy.llinterp_friendly_version = ll_memcpy

def test_labs(n=6):
    assert labs(n) == abs(n)
    assert labs(c_long(0)) == 0
    assert labs(-42) == 42
    return labs(n)

def test_atoi():
    assert atoi("") == 0
    assert atoi("42z7") == 42
    assert atoi("blah") == 0
    assert atoi("18238") == 18238
    A = c_char * 10
    assert atoi(A('\x00')) == 0
    assert atoi(A('4', '2', 'z', '7', '\x00')) == 42
    assert atoi(A('b', 'l', 'a', 'h', '\x00')) == 0
    assert atoi(A('1', '8', '2', '3', '8', '\x00')) == 18238

def test_ll_atoi():
    keepalive = []
    def str2subarray(string):
        llstring = string_repr.convert_const(string)
        keepalive.append(llstring)
        return lltype.direct_arrayitems(unsafe_getfield(llstring, 'chars'))
    assert ll_atoi(str2subarray("")) == 0
    assert ll_atoi(str2subarray("42z7")) == 42
    assert ll_atoi(str2subarray("blah")) == 0
    assert ll_atoi(str2subarray("18238")) == 18238

def test_time():
    import time
    t1 = time.time()
    t2 = time_(None)
    t3 = time.time()
    assert int(t1) <= t2 <= int(t3 + 1.0)

def test_ctime():
    import time
    N = 99999999
    s1 = time.ctime(N)
    s2 = ctime(byref(c_long(N)))
    assert s1.strip() == s2.strip()

##def test_callback():
##    assert callback(100) == 103
##    assert pycallback(100) == 103

class Test_annotation:
    def test_annotate_labs(self):
        a = RPythonAnnotator()
        s = a.build_types(test_labs, [int])
        assert s.knowntype == int
        if conftest.option.view:
            a.translator.view()

    def test_annotate_atoi(self):
        def fn(s):
            return atoi(s)
        a = RPythonAnnotator()
        s = a.build_types(fn, [str])
        assert s.knowntype == int
        if conftest.option.view:
            a.translator.view()

    def test_annotate_reflow_bug(self):
        class Space:
            meth = staticmethod(labs)
            def _freeze_(self):
                return True
        def g(x):
            return x
        def fn(space):
            space.meth(g(0))
            g(-1)
        space = Space()
        def ep():
            return fn(space)
        a = RPythonAnnotator()
        a.build_types(ep, [])
        if conftest.option.view:
            a.translator.view()
    def test_annotate_call_void_p_arg_with_stringbuf(self):
        string = 'abc xyz'
        def f(x):
            buf = create_string_buffer(len(string) + 1)
            res = memcpy(buf, c_char_p(string), len(string))
            return buf.value
        a = RPythonAnnotator()
        s = a.build_types(f, [int])
        if conftest.option.view:
            a.translator.view()
        assert s.knowntype == str

    def test_annotate_call_void_p_arg_with_ptr(self):
        string = 'abc xyz'
        c_char_ptr = POINTER(c_char)
        def f():
            buf = create_string_buffer(len(string) + 1)
            cp = cast(buf, c_char_ptr)
            res = memcpy(cp, c_char_p(string), len(string))
            return buf.value
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        if conftest.option.view:
            a.translator.view()
        assert s.knowntype == str

##    def test_annotate_callback(self):
##        def fn(n):
##            return callback(n)
##        t = TranslationContext()
##        a = t.buildannotator()
##        s = a.build_types(fn, [int])
##        assert s.knowntype == int
##        if conftest.option.view:
##            a.translator.view()
##        graph = graphof(t, mycallback)
##        [v1] = graph.getargs()
##        v2 = graph.getreturnvar()
##        assert a.binding(v1).knowntype == int
##        assert a.binding(v2).knowntype == int

##    def test_annotation_indirectly_found_callback(self):
##        class S(Structure):
##            _fields_ = [('vtable', IntIntCallback*5),
##                        ('z', c_int)]
##        s = S(z=3)
##        s.vtable[2] = callback
##        def fn():
##            return s.z
##        t = TranslationContext()
##        a = t.buildannotator()
##        s = a.build_types(fn, [])
##        assert s.knowntype == int
##        if conftest.option.view:
##            a.translator.view()
##        graph = graphof(t, mycallback)
##        [v1] = graph.getargs()
##        v2 = graph.getreturnvar()
##        assert a.binding(v1).knowntype == int
##        assert a.binding(v2).knowntype == int

    def test_annotate_indirect_call(self):
        s = '442'
        def f(n):
            if n > 0:
                f = strlen
            else:
                f = atol
            return f
        a = RPythonAnnotator()
        s = a.build_types(f, [int])
        if conftest.option.view:
            a.translator.view()
        assert isinstance(s, annmodel.SomeCTypesObject)
        sample = s.knowntype()
        assert list(sample.argtypes) == [c_char_p]
        assert sample.restype == c_long

class Test_specialization:
    def test_specialize_labs(self):
        res = interpret(test_labs, [-11])
        assert res == 11

    def test_specialize_atoi(self):
        choices = ["", "42z7", "blah", "18238"]
        def fn(n):
            return atoi(choices[n])

        res = [interpret(fn, [i]) for i in range(4)]
        assert res == [0, 42, 0, 18238]

    def test_specialize_atoi_char_array(self):
        A = c_char * 10
        choices = [A('\x00'),
                   A('4', '2', 'z', '7', '\x00'),
                   A('b', 'l', 'a', 'h', '\x00'),
                   A('1', '8', '2', '3', '8', '\x00')]
        def fn(n):
            return atoi(choices[n])

        assert fn(3) == 18238
        res = [interpret(fn, [i]) for i in range(4)]
        assert res == [0, 42, 0, 18238]

    def test_specialize_atoi_stringbuf(self):
        def fn(n):
            buf = create_string_buffer(n)
            buf[0] = '4'
            buf[1] = '2'
            return atoi(buf)

        assert fn(11) == 42
        res = interpret(fn, [11])
        assert res == 42

    def test_specialize_call_void_p_arg_with_stringbuf(self):
        string = 'abc xyz'
        def f():
            buf = create_string_buffer(len(string) + 1)
            res = memcpy(buf, c_char_p(string), len(string))
            return buf.value
        assert f() == string
        res = interpret(f, [])
        assert ''.join(res.chars) == string
        

    def test_specialize_call_void_p_arg_with_ptr(self):
        string = 'abc xyz'
        c_char_ptr = POINTER(c_char)
        def f():
            buf = create_string_buffer(len(string) + 1)
            cp = cast(buf, c_char_ptr)
            res = memcpy(cp, c_char_p(string), len(string))
            return buf.value
        res = interpret(f, [])
        assert ''.join(res.chars) == string

class Test_compile:
    def test_compile_labs(self):
        fn = compile(test_labs, [int])
        res = fn(-11)
        assert res == 11

    def test_compile_time(self):
        import time
        def fn1():
            return time_(None)
        fn = compile(fn1, [])
        t1 = time.time()
        t2 = fn()
        t3 = time.time()
        assert int(t1) <= t2 <= int(t3 + 1.0)

    def test_compile_pythonapi(self):
        from pypy.rpython.rctypes import apyobject
        class W_Object(py_object):
            pass
        apyobject.register_py_object_subclass(W_Object)
        PyInt_AsLong = pythonapi.PyInt_AsLong
        PyInt_AsLong.argtypes = [W_Object]
        PyInt_AsLong.restype = c_long
        assert PyInt_AsLong._flags_ & _FUNCFLAG_PYTHONAPI

        PyNumber_Add = pythonapi.PyNumber_Add
        PyNumber_Add.argtypes = [W_Object, W_Object]
        PyNumber_Add.restype = W_Object

        def fn1(x, crash):
            pyobj = W_Object(x)
            pyobj = PyNumber_Add(pyobj, pyobj)
            x = PyInt_AsLong(pyobj)
            if crash:
                # fn(sys.maxint, 1) should crash on PyInt_AsLong before
                # it arrives here.  If by mistake it arrives here then
                # we get a TypeError instead of the OverflowError
                PyNumber_Add(W_Object(5), W_Object("x"))
            return x

        fn = compile(fn1, [int, int])
        res = fn(17, 0)
        assert res == 34
        py.test.raises(OverflowError, 'fn(sys.maxint, 1)')

    def test_compile_pyerrchecker(self):
        from pypy.rpython.rctypes import apyobject
        class W_Object(py_object):
            pass
        apyobject.register_py_object_subclass(W_Object)

        def mypyerrchecker():
            # for this test, always raises
            raise ZeroDivisionError

        PyNumber_Add = pythonapi.PyNumber_Add
        PyNumber_Add.argtypes = [W_Object, W_Object]
        PyNumber_Add.restype = W_Object
        assert PyNumber_Add._flags_ & _FUNCFLAG_PYTHONAPI
        PyNumber_Add._rctypes_pyerrchecker_ = mypyerrchecker
        # special extension ^^^ to support the CPyObjSpace
        try:
            def fn1(n):
                if n < 0:
                    # for this test, force mypyerrchecker() to be annotated
                    # using this trick
                    mypyerrchecker()
                pyobj = W_Object(n)
                return PyNumber_Add(pyobj, pyobj)

            fn = compile(fn1, [int])
            py.test.raises(ZeroDivisionError, fn, 64)
        finally:
            del PyNumber_Add._rctypes_pyerrchecker_

    def test_compile_ctime(self):
        import time
        N = 123456789
        def func(n):
            return ctime(byref(c_long(n)))

        fn = compile(func, [int])
        s1 = time.ctime(N)
        s2 = fn(N)
        assert s1.strip() == s2.strip()

    def test_compile_ctime_vararg(self):
        import time
        N = 101010101
        def func(n):
            args = (byref(c_long(n)),)
            return ctime(*args)

        fn = compile(func, [int])
        s1 = time.ctime(N)
        s2 = fn(N)
        assert s1.strip() == s2.strip()

    def test_compile_call_void_p_arg_with_stringbuf(self):
        string = 'abc xyz'
        def f():
            buf = create_string_buffer(len(string) + 1)
            res = memcpy(buf, c_char_p(string), len(string))
            return buf.value
        assert f() == string
        fn = compile(f, [])
        assert fn() == string
        
    def test_compile_call_void_p_arg_with_ptr(self):
        string = 'abc xyz'
        c_char_ptr = POINTER(c_char)
        def f():
            buf = create_string_buffer(len(string) + 1)
            cp = cast(buf, c_char_ptr)
            res = memcpy(cp, c_char_p(string), len(string))
            return buf.value
        fn = compile(f, [])
        assert fn() == string

    def test_compile_indirect_call(self):
        s = '442'
        def f(n):
            if n > 0:
                f = strlen
            else:
                f = atol
            return f(s)
        fn = compile(f, [int])
        assert fn(1) == 3
        assert fn(0) == 442
