import py
from pypy.jit.timeshifter.test import test_tlc
from pypy.jit.codegen.i386.test.test_genc_portal import I386PortalTestMixin


class TestTLC(I386PortalTestMixin,
              test_tlc.TestTLC):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_tlc.py

    pass
