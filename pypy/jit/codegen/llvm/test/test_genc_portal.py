import py
from pypy.jit.codegen.i386.test.test_genc_portal import I386PortalTestMixin
from pypy.jit.timeshifter.test import test_portal
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp

py.test.skip("WIP")

class LLVMPortalTestMixin(I386PortalTestMixin):
    RGenOp = RLLVMGenOp

class TestPortal(LLVMPortalTestMixin,
                 test_portal.TestPortal):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_portal.py
    pass

