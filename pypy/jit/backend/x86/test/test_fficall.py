import py
from pypy.jit.metainterp.test import test_fficall
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestFfiCall(Jit386Mixin, test_fficall.FfiCallTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_fficall.py
    supports_all = True
