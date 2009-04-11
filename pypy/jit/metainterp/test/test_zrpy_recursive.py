import py
from pypy.jit.metainterp.test import test_recursive
from pypy.jit.metainterp.test.test_zrpy_basic import LLInterpJitMixin


class TestLLRecursive(test_recursive.RecursiveTests, LLInterpJitMixin):
    pass

    # ==========> test_recursive.py
