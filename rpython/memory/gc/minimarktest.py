import sys
from rpython.rtyper.lltypesystem import llarena
from rpython.rtyper.lltypesystem.llmemory import raw_malloc_usage
from rpython.rlib.debug import ll_assert
from rpython.rlib.rarithmetic import LONG_BIT

# For testing, a simple implementation of ArenaCollection.
# This version could be used together with malloc, but
# it requires an extra word per object in the 'all_objects'
# list.

WORD = LONG_BIT // 8


class SimpleArenaCollection(object):

    def __init__(self, arena_size, page_size, small_request_threshold, ok_to_free_func):
        self.arena_size = arena_size   # ignored
        self.page_size = page_size
        self.small_request_threshold = small_request_threshold
        self.ok_to_free_func = ok_to_free_func
        self.all_objects = []
        self.total_memory_used = 0
        self.total_memory_alloced = 0
        self.arenas_count = 0

    def malloc(self, size):
        nsize = raw_malloc_usage(size)
        ll_assert(nsize > 0, "malloc: size is null or negative")
        ll_assert(nsize <= self.small_request_threshold,"malloc: size too big")
        ll_assert((nsize & (WORD-1)) == 0, "malloc: size is not aligned")
        #
        result = llarena.arena_malloc(nsize, False)
        llarena.arena_reserve(result, size)
        self.all_objects.append((result, nsize))
        self.total_memory_used += nsize
        self.total_memory_alloced += nsize
        return result

    def mass_free_prepare(self):
        self.old_all_objects = self.all_objects
        self.all_objects = []
        self.total_memory_used = 0

    def mass_free_incremental(self, max_pages):
        ok_to_free_func = self.ok_to_free_func
        old = self.old_all_objects
        while old:
            rawobj, nsize = old.pop()
            if ok_to_free_func(rawobj):
                llarena.arena_free(rawobj)
                self.total_memory_alloced -= nsize
            else:
                self.all_objects.append((rawobj, nsize))
                self.total_memory_used += nsize
            max_pages -= 0.1
            if max_pages <= 0:
                return False
        return True

    def mass_free(self):
        self.mass_free_prepare()
        res = self.mass_free_incremental(sys.maxint)
        assert res

    def maybe_mass_free_per_class(self, limit_per_class=5):
        return # do nothing in the SimpleArenaCollection.

    def _debug_print_arena_stats(self, *args, **kwargs): pass
