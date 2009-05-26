import py
from pypy.jit.metainterp.test import test_vlist
from pypy.jit.backend.cli.test.test_basic import CliJitMixin


class TestVlist(CliJitMixin, test_vlist.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_vlist.py

    def skip(self):
        py.test.skip("works only after translation")

    test_list_pass_around = skip
    test_cannot_be_virtual = skip
    test_ll_fixed_setitem_fast = skip
