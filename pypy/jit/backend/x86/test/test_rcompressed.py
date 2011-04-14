
from pypy.jit.metainterp.test import test_rcompressed
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestRCompressed(Jit386Mixin, test_rcompressed.TestRCompressed):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_rcompressed.py
    pass
