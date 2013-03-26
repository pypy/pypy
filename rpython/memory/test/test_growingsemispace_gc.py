from rpython.rlib.rarithmetic import LONG_BIT

from rpython.memory.test.test_semispace_gc import TestSemiSpaceGC

WORD = LONG_BIT // 8

class TestGrowingSemiSpaceGC(TestSemiSpaceGC):
    GC_PARAMS = {'space_size': 16*WORD}
