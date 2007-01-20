import py
from pypy.jit.timeshifter.test import test_vlist
from pypy.jit.codegen.i386.test.test_genc_ts import I386TimeshiftingTestMixin


class TestVList(I386TimeshiftingTestMixin,
                test_vlist.TestVList):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_vlist.py

    pass
