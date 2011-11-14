
from pypy.jit.metainterp.test.test_list import ListTests
from pypy.jit.backend.arm.test.support import JitARMMixin
from pypy.jit.backend.arm.test.support import skip_unless_arm
skip_unless_arm()

class TestList(JitARMMixin, ListTests):
    # for individual tests see
    # ====> ../../../metainterp/test/test_list.py
    pass
