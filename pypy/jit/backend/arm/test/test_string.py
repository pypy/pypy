import py
from pypy.jit.metainterp.test import test_string
from pypy.jit.backend.arm.test.support import JitARMMixin

class TestString(JitARMMixin, test_string.TestLLtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_string.py
    pass

class TestUnicode(JitARMMixin, test_string.TestLLtypeUnicode):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_string.py
    pass
