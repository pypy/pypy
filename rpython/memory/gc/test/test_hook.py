from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.memory.gc.hook import GcHooks
from rpython.memory.gc.test.test_direct import BaseDirectGCTest, S

class MyGcHooks(GcHooks):

    def __init__(self):
        self.reset()

    def reset(self):
        self.minors = []
        self.collects = []

    def on_gc_minor(self, **kwds):
        self.minors.append(kwds)

    def on_gc_collect(self, **kwds):
        self.collects.append(kwds)


class TestIncMiniMarkHooks(BaseDirectGCTest):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass

    def get_extra_gc_params(self):
        return {'hooks': MyGcHooks()}

    def setup_method(self, m):
        BaseDirectGCTest.setup_method(self, m)
        size = llmemory.sizeof(S) + self.gc.gcheaderbuilder.size_gc_header
        self.size_of_S = llmemory.raw_malloc_usage(size)

    def test_on_gc_minor(self):
        self.malloc(S)
        self.gc._minor_collection()
        assert self.gc.hooks.minors == [
            {'total_memory_used': 0, 'pinned_objects': 0}
            ]
        self.gc.hooks.reset()
        #
        # these objects survive, so the total_memory_used is > 0
        self.stackroots.append(self.malloc(S))
        self.stackroots.append(self.malloc(S))
        self.gc._minor_collection()
        assert self.gc.hooks.minors == [
            {'total_memory_used': self.size_of_S*2, 'pinned_objects': 0}
            ]

    def test_on_gc_collect(self):
        self.malloc(S)
        self.gc.collect()
        assert self.gc.hooks.collects == [
            {'count': 1,
             'arenas_count_before': 0,
             'arenas_count_after': 0,
             'arenas_bytes': 0,
             'rawmalloc_bytes_after': 0,
             'rawmalloc_bytes_before': 0}
            ]
        self.gc.hooks.reset()
        #
        self.stackroots.append(self.malloc(S))
        self.gc.collect()
        assert self.gc.hooks.collects == [
            {'count': 2,
             'arenas_count_before': 1,
             'arenas_count_after': 1,
             'arenas_bytes': self.size_of_S,
             'rawmalloc_bytes_after': 0,
             'rawmalloc_bytes_before': 0}
            ]
