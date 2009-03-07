import py
from pypy.jit.metainterp.test import test_slist
from pypy.jit.metainterp.test.test_zrpy_basic import LLInterpJitMixin


class TestLLList(test_slist.ListTests, LLInterpJitMixin):
    pass
