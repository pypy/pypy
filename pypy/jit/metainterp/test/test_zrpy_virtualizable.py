import py
py.test.skip("later")
from pypy.jit.metainterp.test import test_virtualizable
from pypy.jit.metainterp.test.test_zrpy_basic import LLInterpJitMixin


class TestLLImplicitVirtualizable(LLInterpJitMixin,
                       test_virtualizable.ImplicitVirtualizableTests):
    pass
