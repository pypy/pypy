"""
Test external function calls using the custom extension module _rctypes_test.c.
"""

import py
import pypy.rpython.rctypes.implementation
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy.translator.c.test.test_genc import compile, compile_db
from pypy.translator.tool.cbuild import compile_c_module
from pypy.annotation.model import SomeCTypesObject, SomeObject
from pypy import conftest
import sys
from pypy.rpython.test.test_llinterp import interpret

thisdir = py.path.local(__file__).dirpath()

from ctypes import cdll
from ctypes import POINTER, Structure, c_int, byref, pointer, c_void_p
from ctypes import CFUNCTYPE

# __________ compile and load our local test C file __________

# LoadLibrary is deprecated in ctypes, this should be removed at some point
if "load" in dir(cdll):
    cdll_load = cdll.load
else:
    cdll_load = cdll.LoadLibrary

# XXX the built module and intermediate files should go to /tmp/usession-*,
#     see pypy.tool.udir
c_source = thisdir.join("_rctypes_test.c")
compile_c_module([c_source], "_rctypes_test")
includes = (str(c_source),)   # in the sequel, we #include the whole .c file
del c_source                  # into the generated C sources

if sys.platform == "win32":
    _rctypes_test = cdll_load(str(thisdir.join("_rctypes_test.pyd")))
else:
    _rctypes_test = cdll_load(str(thisdir.join("_rctypes_test.so")))

# struct tagpoint
class tagpoint(Structure):
    _fields_ = [("x", c_int),
                ("y", c_int),
                ("_z", c_int)]
    _external_ = True       # hack to avoid redeclaration of the struct in C

# _test_struct
testfunc_struct = _rctypes_test._testfunc_struct
testfunc_struct.restype = c_int
testfunc_struct.argtypes = [tagpoint]

def ll_testfunc_struct(in_):
    return in_.c_x + in_.c_y
testfunc_struct.llinterp_friendly_version = ll_testfunc_struct
testfunc_struct.includes = includes

# _testfunc_byval
testfunc_byval = _rctypes_test._testfunc_byval
testfunc_byval.restype = c_int
testfunc_byval.argtypes = [tagpoint, POINTER(tagpoint)]

def ll_testfunc_byval(in_, pout):
    if pout:
        pout.c_x = in_.c_x
        pout.c_y = in_.c_y
    return in_.c_x + in_.c_y
testfunc_byval.llinterp_friendly_version = ll_testfunc_byval
testfunc_byval.includes = includes

# _test_struct_id
# XXX no support for returning structs
#testfunc_struct_id = _rctypes_test._testfunc_struct_id
#testfunc_struct_id.restype = tagpoint
#testfunc_struct_id.argtypes = [tagpoint]

# _test_struct_id_pointer
tagpointptr = POINTER(tagpoint)
testfunc_struct_pointer_id = _rctypes_test._testfunc_struct_pointer_id
testfunc_struct_pointer_id.restype = tagpointptr
testfunc_struct_pointer_id.argtypes = [tagpointptr]

def ll_testfunc_struct_pointer_id(pin):
    return pin
testfunc_struct_pointer_id.llinterp_friendly_version = (
    ll_testfunc_struct_pointer_id)
testfunc_struct_pointer_id.includes = includes

# _testfunc_swap
testfunc_swap = _rctypes_test._testfunc_swap
testfunc_swap.restype = None
testfunc_swap.argtypes = [tagpointptr]

def ll_testfunc_swap(p):
    p.c_x, p.c_y = p.c_y, p.c_x
    p.c__z += 1
testfunc_swap.llinterp_friendly_version = ll_testfunc_swap
testfunc_swap.includes = includes

# _testfunc_swap2
testfunc_swap2 = _rctypes_test._testfunc_swap2
testfunc_swap2.restype = None
testfunc_swap2.argtypes = [tagpointptr]

def ll_testfunc_swap2(p):
    p.c_x, p.c_y = p.c_y, p.c_x
    p.c__z += 2
testfunc_swap2.llinterp_friendly_version = ll_testfunc_swap2
testfunc_swap2.includes = includes

# _testfunc_erase_type
testfunc_erase_type = _rctypes_test._testfunc_erase_type
testfunc_erase_type.restype = c_void_p
testfunc_erase_type.argtypes = []

# _testfunc_get_func
testfunc_get_func = _rctypes_test._testfunc_get_func
testfunc_get_func.restype = CFUNCTYPE(c_int, tagpoint)
testfunc_get_func.argtypes = []
testfunc_get_func.includes = includes


def test_testfunc_struct():
    in_point = tagpoint()
    in_point.x = 42
    in_point.y = 17
    res = testfunc_struct(in_point)
    assert res == in_point.x + in_point.y
    return in_point.x - in_point.y     # this test function is reused below

def test_testfunc_byval():
    in_point = tagpoint()
    in_point.x = 42
    in_point.y = 17
    out_point = tagpoint()
    res = testfunc_byval(in_point, byref(out_point))
    assert res == in_point.x + in_point.y
    assert out_point.x == 42
    assert out_point.y == 17
    return out_point.x - out_point.y     # this test function is reused below

def test_testfunc_struct_pointer_id():
    in_point = tagpoint()
    in_point.x = 42
    in_point.y = 17
    res = testfunc_struct_pointer_id(byref(in_point))
    res.contents.x //= 2
    assert in_point.x == 21
    return in_point.x - in_point.y       # this test function is reused below

def test_testfunc_swap():
    pt = tagpoint()
    pt.x = 5
    pt.y = 9
    pt._z = 99
    testfunc_swap(pointer(pt))
    assert pt.x == 9
    assert pt.y == 5
    assert pt._z == 100
    return pt.x - pt.y                   # this test function is reused below

def test_testfunc_get_func():
    in_point = tagpoint()
    in_point.x = -9171831
    in_point.y = 9171873
    fn = testfunc_get_func()
    res = fn(in_point)
    assert res == 42
    return res       # this test function is reused below

class Test_annotation:
    def test_annotate_struct(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(test_testfunc_struct, [])
        if conftest.option.view:
            t.view()
        assert s.knowntype == int

    def test_annotate_byval(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(test_testfunc_byval, [])
        if conftest.option.view:
            t.view()
        assert s.knowntype == int

class Test_specialization:
    def test_specialize_struct(self):
        res = interpret(test_testfunc_struct, [])
        assert res == 42 - 17

    def test_specialize_byval(self):
        res = interpret(test_testfunc_byval, [])
        assert res == 42 - 17

    def test_specialize_struct_pointer_id(self):
        res = interpret(test_testfunc_struct_pointer_id, [])
        assert res == 21 - 17

    def test_specialize_None_as_null_pointer(self):
        def fn():
            res = testfunc_struct_pointer_id(None)
            return bool(res)
        res = interpret(fn, [])
        assert res is False

    def test_specialize_swap(self):
        res = interpret(test_testfunc_swap, [])
        assert res == 4

    def test_specialize_indirect_call(self):
        def f(n):
            pt = tagpoint()
            pt.x = 5
            pt.y = 9
            pt._z = 99
            if n > 0:
                f = testfunc_swap
            else:
                f = testfunc_swap2
            f(pointer(pt))
            assert pt.x == 9
            assert pt.y == 5
            return pt._z
        res = interpret(f, [42])
        assert res == 100
        res = interpret(f, [-42])
        assert res == 101

class Test_compile:
    def test_compile_byval(self):
        fn = compile(test_testfunc_byval, [])
        assert fn() == 42 - 17

    def test_compile_struct_pointer_id(self):
        fn = compile(test_testfunc_struct_pointer_id, [])
        assert fn() == 21 - 17

    def test_compile_swap(self):
        fn = compile(test_testfunc_swap, [])
        assert fn() == 4

    def test_compile_get_func(self):
        fn = compile(test_testfunc_get_func, [])
        assert fn() == 42
