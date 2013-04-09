from rpython.memory.test.test_semispace_gc import TestSemiSpaceGC

class TestGenerationalGC(TestSemiSpaceGC):
    from rpython.memory.gc.generation import GenerationGC as GCClass
