
import py
from pypy.jit.metainterp.test import test_zrpy_del
from pypy.jit.backend.x86.test.test_zrpy_slist import Jit386Mixin

class TestDel(Jit386Mixin, test_zrpy_del.TestLLDels):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_del.py
    pass
