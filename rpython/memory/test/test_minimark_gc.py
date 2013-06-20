from rpython.rlib.rarithmetic import LONG_BIT

from rpython.memory.test import test_semispace_gc

WORD = LONG_BIT // 8

class TestMiniMarkGC(test_semispace_gc.TestSemiSpaceGC):
    from rpython.memory.gc.minimark import MiniMarkGC as GCClass
    GC_CAN_SHRINK_BIG_ARRAY = False
    GC_CAN_MALLOC_NONMOVABLE = True
    BUT_HOW_BIG_IS_A_BIG_STRING = 11*WORD
