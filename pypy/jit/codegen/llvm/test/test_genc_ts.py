import py
from pypy.jit.codegen.i386.test.test_genc_ts import I386TimeshiftingTestMixin
from pypy.jit.timeshifter.test import test_timeshift
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp


class LLVMTimeshiftingTestMixin(I386TimeshiftingTestMixin):
    RGenOp = RLLVMGenOp

py.test.skip("WIP")

class TestTimeshiftLLVM(LLVMTimeshiftingTestMixin,
                        test_timeshift.TestTimeshift):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_timeshift.py

    pass

