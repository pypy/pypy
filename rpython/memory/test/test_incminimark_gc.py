from rpython.rlib.rarithmetic import LONG_BIT

from rpython.memory.test import test_minimark_gc

class TestIncrementalMiniMarkGC(test_minimark_gc.TestMiniMarkGC):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass
