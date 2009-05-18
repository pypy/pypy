import py
from pypy.jit.backend.cli.test.test_zrpy_basic import CliTranslatedJitMixin
from pypy.jit.metainterp.test import test_slist


class TestSList(CliTranslatedJitMixin, test_slist.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_slist.py

    def skip(self):
        py.test.skip('in-progress')


    test_lazy_getitem_4 = skip
