
from pypy.jit.metainterp.test.test_recursive import RecursiveTests
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestRecursive(Jit386Mixin, RecursiveTests):
    pass
