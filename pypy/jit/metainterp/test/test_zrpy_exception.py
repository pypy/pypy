import py
from pypy.jit.metainterp.test import test_exception
from pypy.jit.metainterp.test.test_zrpy_basic import LLInterpJitMixin
from pypy.rlib.jit import JitDriver

class TestLLExceptions(test_exception.ExceptionTests, LLInterpJitMixin):
    def interp_operations(self, *args, **kwds):
        py.test.skip("uses interp_operations()")

    # ==========> test_exception.py

    def test_raise(self): skip1()
    def test_raise_through(self): skip1()
    def test_raise_through_wrong_exc(self): skip1()
    def test_raise_through_wrong_exc_2(self): skip1()

def skip1():
    py.test.skip("the portal always raises, causing blocked blocks")
