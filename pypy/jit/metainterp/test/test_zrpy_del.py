import py
from pypy.jit.metainterp.test import test_del
from pypy.jit.metainterp.test.test_zrpy_basic import LLInterpJitMixin

class TestLLDels(test_del.DelTests, LLInterpJitMixin):
    pass
    # ==========> test_del.py
