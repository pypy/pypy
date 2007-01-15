import py
py.test.skip("in-progress")
from pypy.jit.timeshifter.test import test_tlr
from pypy.jit.codegen.i386.test.test_genc_portal import I386PortalTestMixin


class TestTLR(I386PortalTestMixin,
              test_tlr.TestTLR):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_tlr.py

    pass
