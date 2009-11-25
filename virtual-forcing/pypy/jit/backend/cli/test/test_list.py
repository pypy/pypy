import py
from pypy.jit.metainterp.test import test_list
from pypy.jit.backend.cli.test.test_basic import CliJitMixin


class TestVlist(CliJitMixin, test_list.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_list.py

    def skip(self):
        py.test.skip("works only after translation")

    test_list_pass_around = skip
    test_cannot_be_virtual = skip
    test_ll_fixed_setitem_fast = skip
