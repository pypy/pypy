from rpython.translator.jvm.test.runtest import JvmTest
from rpython.rlib.longlong2float import *
from rpython.rlib.test.test_longlong2float import enum_floats
from rpython.rlib.test.test_longlong2float import fn as float2longlong2float
import py

class TestLongLong2Float(JvmTest):

    def test_float2longlong_and_longlong2float(self):
        def func(f):
            return float2longlong2float(f)

        for f in enum_floats():
            assert repr(f) == repr(self.interpret(func, [f]))

    def test_uint2singlefloat(self):
        py.test.skip("uint2singlefloat is not implemented in ootype")

    def test_singlefloat2uint(self):
        py.test.skip("singlefloat2uint is not implemented in ootype")
