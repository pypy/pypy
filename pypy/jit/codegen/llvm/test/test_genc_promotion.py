import py
from pypy.jit.timeshifter.test import test_promotion
from pypy.jit.codegen.llvm.test.test_genc_ts import LLVMTimeshiftingTestMixin

py.test.skip("WIP")

class TestPromotion(LLVMTimeshiftingTestMixin,
                    test_promotion.TestPromotion):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_promotion.py
    pass
