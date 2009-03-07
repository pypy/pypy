
from pypy.jit.metainterp.test.test_vlist import ListTests
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestVList(Jit386Mixin, ListTests):
    # for individual tests see
    # ====> ../../../metainterp/test/test_vlist.py
    pass
