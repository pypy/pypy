import py
from pypy.jit.metainterp.test import test_send
from pypy.jit.metainterp.test.test_zrpy_basic import LLInterpJitMixin


class TestLLSend(test_send.SendTests, LLInterpJitMixin):
    pass
