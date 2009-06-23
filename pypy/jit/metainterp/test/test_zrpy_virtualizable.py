import py
from pypy.jit.metainterp.test import test_virtualizable
from pypy.jit.metainterp.test.test_zrpy_basic import LLInterpJitMixin


class TestLLVirtualizable(LLInterpJitMixin,
                          test_virtualizable.ExplicitVirtualizableTests):
    pass
