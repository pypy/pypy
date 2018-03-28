from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.memory.gc.hook import GcHooks
from rpython.memory.gc.test.test_direct import BaseDirectGCTest, S

class MyGcHooks(GcHooks):

    def __init__(self):
        self.reset()

    def reset(self):
        self.minors = []

    def on_gc_minor(self, **kwds):
        self.minors.append(kwds)


class TestIncMiniMarkHooks(BaseDirectGCTest):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass

    def get_extra_gc_params(self):
        return {'hooks': MyGcHooks()}

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
        size = llmemory.sizeof(S) + self.gc.gcheaderbuilder.size_gc_header
        rawsize = llmemory.raw_malloc_usage(size)
        self.gc._minor_collection()
        assert self.gc.hooks.minors == [
            {'total_memory_used': rawsize*2, 'pinned_objects': 0}
            ]
