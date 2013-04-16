import py
from rpython.jit.backend.cli.test.test_zrpy_basic import CliTranslatedJitMixin
from rpython.jit.metainterp.test import test_list


class TestVList(CliTranslatedJitMixin, test_list.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_list.py

    pass
