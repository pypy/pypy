import py
py.test.skip('decide what to do')
from rpython.jit.backend.cli.test.test_zrpy_basic import CliTranslatedJitMixin
from rpython.jit.metainterp.test import test_slist


class TestSList(CliTranslatedJitMixin, test_slist.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_slist.py
    pass
