import py
from pypy.jit.timeshifter.test import test_exception
from pypy.jit.codegen.i386.test.test_genc_ts import I386TimeshiftingTestMixin


class TestException(I386TimeshiftingTestMixin,
                    test_exception.TestException):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_exception.py

    pass
