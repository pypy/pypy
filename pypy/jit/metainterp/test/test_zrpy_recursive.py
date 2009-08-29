import py, sys
from pypy.jit.metainterp.test import test_recursive
from pypy.jit.metainterp.test.test_zrpy_basic import LLInterpJitMixin


class TestLLRecursive(test_recursive.RecursiveTests, LLInterpJitMixin):

    def setup_class(cls):
        cls._recursion_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(5000)

    def teardown_class(cls):
        sys.setrecursionlimit(cls._recursion_limit)

    # ==========> test_recursive.py

    @py.test.mark.xfail
    def test_inline_faulty_can_inline(self):
        test_recursive.RecursiveTests.test_inline_faulty_can_inline(self)
