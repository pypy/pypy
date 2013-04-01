from rpython.memory.test.test_minimark_gc import TestMiniMarkGC

class TestMiniMarkGCCardMarking(TestMiniMarkGC):
    GC_PARAMS = {'card_page_indices': 4}
