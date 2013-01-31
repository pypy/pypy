from pypy.rpython.lltypesystem import llarena
from pypy.rpython.lltypesystem.llmemory import raw_malloc_usage
from pypy.rlib.debug import ll_assert
from pypy.rlib.rarithmetic import LONG_BIT

# For testing, a simple implementation of ArenaCollection.
# This version could be used together with obmalloc.c, but
# it requires an extra word per object in the 'all_objects'
# list.

WORD = LONG_BIT // 8


class SimpleArenaCollection(object):

    def __init__(self, arena_size, page_size, small_request_threshold):
        self.arena_size = arena_size   # ignored
        self.page_size = page_size
        self.small_request_threshold = small_request_threshold
        self.all_objects = []
        self.total_memory_used = 0

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
        return result

    def mass_free(self, ok_to_free_func):
        objs = self.all_objects
        self.all_objects = []
        self.total_memory_used = 0
        for rawobj, nsize in objs:
            if ok_to_free_func(rawobj):
                llarena.arena_free(rawobj)
            else:
                self.all_objects.append((rawobj, nsize))
                self.total_memory_used += nsize
