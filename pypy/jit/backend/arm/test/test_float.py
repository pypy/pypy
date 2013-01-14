
import py
from pypy.jit.backend.arm.test.support import JitARMMixin
from pypy.jit.metainterp.test.test_float import FloatTests

class TestFloat(JitARMMixin, FloatTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_float.py
    pass
