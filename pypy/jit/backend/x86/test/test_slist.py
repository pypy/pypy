
from pypy.jit.metainterp.test import test_slist, test_dlist
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestSList(Jit386Mixin, test_slist.ListTests, test_dlist.ListTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_slist.py
    # ====> ../../../metainterp/test/test_dlist.py
    pass
