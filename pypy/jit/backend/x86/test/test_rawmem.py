
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin
from pypy.jit.metainterp.test.test_rawmem import RawMemTests


class TestRawMem(Jit386Mixin, RawMemTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_rawmem.py
    pass
