from pypy.jit.metainterp.test import test_longlong
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestLongLong(Jit386Mixin, test_longlong.LongLongTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_longlong.py
    pass
