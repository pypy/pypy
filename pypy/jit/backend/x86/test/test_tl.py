
import py
from pypy.jit.metainterp.test.test_tl import ToyLanguageTests
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestTL(Jit386Mixin, ToyLanguageTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_tl.py
    pass

