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

try:
    import ctypes
except ImportError:
    py.test.skip("this test needs ctypes installed")


from ctypes import cdll
from ctypes import POINTER, Structure, c_int, byref

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
    _rctypes_test = cdll_load("_rctypes_test.pyd")
else:
    _rctypes_test = cdll_load(str(thisdir.join("_rctypes_test.so")))

# struct tagpoint
class tagpoint(Structure):
    _fields_ = [("x", c_int),
                ("y", c_int)]
    _external_ = True       # hack to avoid redeclaration of the struct in C

# _testfunc_byval
testfunc_byval = _rctypes_test._testfunc_byval
testfunc_byval.restype = c_int
testfunc_byval.argtypes = [tagpoint, POINTER(tagpoint)]

def ll_testfunc_byval(in_, pout):
    if pout:
        pout.x = in_.x
        pout.y = in_.y
    return in_.x + in_.y
testfunc_byval.llinterp_friendly_version = ll_testfunc_byval
testfunc_byval.includes = includes

# _test_struct
testfunc_struct = _rctypes_test._testfunc_struct
testfunc_struct.restype = c_int
testfunc_struct.argtypes = [tagpoint]

# _test_struct_id
testfunc_struct_id = _rctypes_test._testfunc_struct_id
testfunc_struct_id.restype = tagpoint
testfunc_struct_id.argtypes = [tagpoint]

# _test_struct_id_pointer
tagpointptr = POINTER(tagpoint)
testfunc_struct_pointer_id = _rctypes_test._testfunc_struct_pointer_id
testfunc_struct_pointer_id.restype = tagpointptr
testfunc_struct_pointer_id.argtypes = [tagpointptr]


def test_rctypes_dll():
    in_point = tagpoint()
    in_point.x = 42
    in_point.y = 17
    out_point = tagpoint()
    res = testfunc_byval(in_point, byref(out_point))
    assert res == in_point.x + in_point.y
    assert out_point.x == 42
    assert out_point.y == 17
    return out_point.x - out_point.y     # this test function is reused below

class Test_annotation:
    def test_annotate_byval(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(test_rctypes_dll, [])
        if conftest.option.view:
            t.view()
        assert s.knowntype == int

class Test_specialization:
    def test_specialize_byval(self):
        res = interpret(test_rctypes_dll, [])
        assert res == 42 - 17

class Test_compile:
    def test_compile_byval(self):
        fn = compile(test_rctypes_dll, [])
        assert fn() == 42 - 17
