
from pypy.jit.metainterp.test.test_list import ListTests
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestList(Jit386Mixin, ListTests):
    # for individual tests see
    # ====> ../../../metainterp/test/test_list.py
    pass
