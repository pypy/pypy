import py
from pypy.jit.backend.cli.test.test_zrpy_basic import CliTranslatedJitMixin
from pypy.jit.metainterp.test import test_exception


class TestException(CliTranslatedJitMixin, test_exception.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_exception.py

    pass

