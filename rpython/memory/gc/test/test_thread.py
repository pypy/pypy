import pytest
from rpython.rtyper.lltypesystem import lltype
from rpython.memory.gc import incminimark
from rpython.memory.gc.test.test_direct import BaseDirectGCTest, S


class LocalsForTests:
    pass


class ThreadSwitcher:
    all_threadlocals = [incminimark.NURSERY_FREE,
                        incminimark.NURSERY_TOP,
                        incminimark.NEXT_NUBLOCK,
                        ]

    def __init__(self):
        self.cache = {}
        self.switch_thread(0)

    def switch_thread(self, thread_num):
        for tl in self.all_threadlocals:
            tl.local = self.cache.setdefault((tl, thread_num), LocalsForTests())


class TestMultithreaded(BaseDirectGCTest):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass

    def test_malloc_fixedsize(self):
        ts = ThreadSwitcher()
        for i in range(1000):
            p = self.malloc(S)
            p.x = 42
            assert p.prev == lltype.nullptr(S)
            assert p.next == lltype.nullptr(S)
            ts.switch_thread(i & 1)
        #...
