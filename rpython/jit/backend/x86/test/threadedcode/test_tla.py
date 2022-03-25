import py
from rpython.jit.tl.threadedcode.test.test_tla import TestLLType
from rpython.jit.backend.x86.test.test_basic import Jit386Mixin

class TestTL(Jit386Mixin, TestLLType):
    # for the individual tests see
    # ====> ../../../tl/threadedcode/test/test_tla.py
    pass
