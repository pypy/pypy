import py
py.test.skip('decide what to do')
from pypy.jit.backend.cli.test.test_zrpy_basic import CliTranslatedJitMixin
from pypy.jit.metainterp.test import test_slist


class TestSList(CliTranslatedJitMixin, test_slist.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_slist.py
    pass
