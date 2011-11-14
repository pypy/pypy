
from pypy.jit.metainterp.test.test_recursive import RecursiveTests
from pypy.jit.backend.arm.test.support import JitARMMixin
from pypy.jit.backend.arm.test.support import skip_unless_arm
skip_unless_arm()

class TestRecursive(JitARMMixin, RecursiveTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_recursive.py
    pass
