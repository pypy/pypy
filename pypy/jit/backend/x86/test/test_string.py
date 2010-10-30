import py
from pypy.jit.metainterp.test import test_string
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestString(Jit386Mixin, test_string.TestLLtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_string.py
    pass

class TestUnicode(Jit386Mixin, test_string.TestLLtypeUnicode):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_string.py
    pass
