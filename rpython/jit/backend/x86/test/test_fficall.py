import py
from rpython.jit.metainterp.test import test_fficall
from rpython.jit.backend.x86.test.test_basic import Jit386Mixin

class TestFfiCall(Jit386Mixin, test_fficall.FfiCallTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_fficall.py
    pass
