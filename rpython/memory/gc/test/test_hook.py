from rpython.rlib.rarithmetic import intmask
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.memory.gc.hook import GcHooks
from rpython.memory.gc.test.test_direct import BaseDirectGCTest, S


# The following class is used also by test_transformed_gc and so it needs to
# be RPython, that's why we have to use intmask to get consistent types
class MyGcHooks(GcHooks):

    def __init__(self):
        GcHooks.__init__(self)
        self.reset()

    def reset(self):
        self.minors = []
        self.steps = []
        self.collects = []

    def on_gc_minor(self, total_memory_used, pinned_objects):
        self.minors.append({
            'total_memory_used': intmask(total_memory_used),
            'pinned_objects': pinned_objects})

    def on_gc_collect_step(self, oldstate, newstate):
        self.steps.append({
            'oldstate': oldstate,
            'newstate': newstate})

    def on_gc_collect(self, count, arenas_count_before, arenas_count_after,
                      arenas_bytes, rawmalloc_bytes_before,
                      rawmalloc_bytes_after):
        self.collects.append({
            'count': count,
            'arenas_count_before': arenas_count_before,
            'arenas_count_after': arenas_count_after,
            'arenas_bytes': intmask(arenas_bytes),
            'rawmalloc_bytes_before': intmask(rawmalloc_bytes_before),
            'rawmalloc_bytes_after': intmask(rawmalloc_bytes_after)})


class TestIncMiniMarkHooks(BaseDirectGCTest):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass

    def get_extra_gc_params(self):
        return {'hooks': MyGcHooks()}

    def setup_method(self, m):
        BaseDirectGCTest.setup_method(self, m)
        size = llmemory.sizeof(S) + self.gc.gcheaderbuilder.size_gc_header
        self.size_of_S = llmemory.raw_malloc_usage(size)

    def test_on_gc_minor(self):
        self.gc.hooks.gc_minor_enabled = True
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
        from rpython.memory.gc import incminimark as m
        self.gc.hooks.gc_collect_step_enabled = True
        self.gc.hooks.gc_collect_enabled = True
        self.malloc(S)
        self.gc.collect()
        assert self.gc.hooks.steps == [
            {'oldstate': m.STATE_SCANNING, 'newstate': m.STATE_MARKING},
            {'oldstate': m.STATE_MARKING, 'newstate': m.STATE_SWEEPING},
            {'oldstate': m.STATE_SWEEPING, 'newstate': m.STATE_FINALIZING},
            {'oldstate': m.STATE_FINALIZING, 'newstate': m.STATE_SCANNING}
        ]
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

    def test_hook_disabled(self):
        self.gc._minor_collection()
        self.gc.collect()
        assert self.gc.hooks.minors == []
        assert self.gc.hooks.steps == []
        assert self.gc.hooks.collects == []
