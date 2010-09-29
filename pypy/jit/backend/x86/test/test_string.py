import py
from pypy.jit.metainterp.test import test_string
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestString(Jit386Mixin, test_string.StringTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_string.py
    CALL = 'call'
    CALL_PURE = 'call_pure'
