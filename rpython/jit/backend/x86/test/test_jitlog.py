
from rpython.jit.backend.x86.test.test_basic import Jit386Mixin
from rpython.jit.backend.test.jitlog_test import LoggerTest

class TestJitlog(Jit386Mixin, LoggerTest):
    # for the individual tests see
    # ====> ../../../test/jitlog_test.py
    pass
