
import py
from pypy.jit.metainterp.test.test_recursive import RecursiveTests
from pypy.jit.backend.x86.test.test_zrpy_slist import Jit386Mixin

class TestRecursive(Jit386Mixin, RecursiveTests):

    def test_inline_faulty_can_inline(self):
        py.test.skip("this test is not supposed to be translated")
