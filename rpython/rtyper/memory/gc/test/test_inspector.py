import os
from pypy.tool.udir import udir
from rpython.rtyper.memory.gc.test.test_direct import BaseDirectGCTest, S
from rpython.rtyper.memory.gc import inspector
from rpython.rtyper.lltypesystem import llmemory


class InspectorTest(BaseDirectGCTest):

    def test_dump_rpy_heap(self):
        p = self.malloc(S)
        p.x = 5
        q = self.malloc(S)
        q.x = 6
        self.write(p, 'next', q)
        self.stackroots.append(p)
        #
        saved = inspector.HeapDumper.flush.im_func
        try:
            seen = []
            def my_flush(self):
                for i in range(self.buf_count):
                    seen.append(self.writebuffer[i])
                self.buf_count = 0
            inspector.HeapDumper.flush = my_flush
            inspector.dump_rpy_heap(self.gc, -123456)
        finally:
            inspector.HeapDumper.flush = saved
        #
        class ASize(object):
            def __eq__(self, other):
                return isinstance(other, llmemory.AddressOffset)
        adr_p = seen[0]
        adr_q = seen[3]
        expected = [adr_p, 1, ASize(), adr_q, -1,
                    0, 0, 0, -1,
                    adr_q, 1, ASize(), -1]
        assert expected == seen


class TestHybridGC(InspectorTest):
    from rpython.rtyper.memory.gc.hybrid import HybridGC as GCClass

class TestMiniMarkGCSimple(InspectorTest):
    from rpython.rtyper.memory.gc.minimark import MiniMarkGC as GCClass
    from rpython.rtyper.memory.gc.minimark import SimpleArenaCollection
    GC_PARAMS = {'ArenaCollectionClass': SimpleArenaCollection,
                 "card_page_indices": 4}
