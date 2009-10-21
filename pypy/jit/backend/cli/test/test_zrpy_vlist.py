import py
from pypy.jit.backend.cli.test.test_zrpy_basic import CliTranslatedJitMixin
from pypy.jit.metainterp.test import test_vlist


class TestVList(CliTranslatedJitMixin, test_vlist.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_vlist.py

    # disable the xfail()
    def test_vlist_alloc_and_set(self):
        test_vlist.TestOOtype.test_vlist_alloc_and_set(self)
