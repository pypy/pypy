
from pypy.jit.metainterp.test.test_list import ListTests
from pypy.jit.backend.arm.test.support import JitARMMixin

class TestList(JitARMMixin, ListTests):
    # for individual tests see
    # ====> ../../../metainterp/test/test_list.py
    pass
