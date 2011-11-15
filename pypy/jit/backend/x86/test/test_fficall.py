import py
from pypy.jit.metainterp.test import test_fficall
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestFfiLookups(Jit386Mixin, test_fficall.FfiLookupTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_fficall.py
    supports_all = True
