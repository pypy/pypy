import sys
from pypy.rlib.rarithmetic import intmask, r_uint
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib import rmmap
from pypy.rpython.lltypesystem import lltype, llmemory, rffi


class AsmMemoryManager(object):
    LARGE_ALLOC_SIZE = 1024 * 1024   # 1MB
    MIN_FRAGMENT = 64
    NUM_INDICES = 32     # good for all sizes between 64 bytes and ~490 KB

    def __init__(self, large_alloc_size = LARGE_ALLOC_SIZE,
                       min_fragment     = MIN_FRAGMENT,
                       num_indices      = NUM_INDICES):
        self.total_memory_allocated = r_uint(0)
        self.large_alloc_size = large_alloc_size
        self.min_fragment = min_fragment
        self.num_indices = num_indices
        self.free_blocks = {}      # map {start: stop}
        self.free_blocks_end = {}  # map {stop: start}
        self.blocks_by_size = [[] for i in range(self.num_indices)]
        self._allocated = []

    def malloc(self, minsize, maxsize):
        """Allocate executable memory, between minsize and maxsize bytes,
        and return a pair (start, stop).  Does not perform any rounding
        of minsize and maxsize.
        """
        result = self._allocate_block(minsize)
        (start, stop) = result
        smaller_stop = start + maxsize
        if smaller_stop + self.min_fragment <= stop:
            result = (start, smaller_stop)
            self._add_free_block(smaller_stop, stop)
        return result   # pair (start, stop)

    def free(self, start, stop):
        """Free a block (start, stop) returned by a previous malloc()."""
        self._add_free_block(start, stop)

    def _allocate_large_block(self, minsize):
        # Compute 'size' from 'minsize': it must be rounded up to
        # 'large_alloc_size'.  Additionally, we use the following line
        # to limit how many mmap() requests the OS will see in total:
        minsize = max(minsize, intmask(self.total_memory_allocated >> 4))
        size = minsize + self.large_alloc_size - 1
        size = (size // self.large_alloc_size) * self.large_alloc_size
        data = rmmap.alloc(size)
        if not we_are_translated():
            self._allocated.append((data, size))
            if sys.maxint > 2147483647:
                # Hack to make sure that mcs are not within 32-bits of one
                # another for testing purposes
                rmmap.hint.pos += 0x80000000 - size
        self.total_memory_allocated += size
        data = rffi.cast(lltype.Signed, data)
        return self._add_free_block(data, data + size)

    def _get_index(self, length):
        i = 0
        while length > self.min_fragment:
            length = (length * 3) >> 2
            i += 1
            if i == self.num_indices - 1:
                break
        return i

    def _add_free_block(self, start, stop):
        # Merge with the block on the left
        if start in self.free_blocks_end:
            left_start = self.free_blocks_end[start]
            self._del_free_block(left_start, start)
            start = left_start
        # Merge with the block on the right
        if stop in self.free_blocks:
            right_stop = self.free_blocks[stop]
            self._del_free_block(stop, right_stop)
            stop = right_stop
        # Add it to the dicts
        self.free_blocks[start] = stop
        self.free_blocks_end[stop] = start
        i = self._get_index(stop - start)
        self.blocks_by_size[i].append(start)
        return start

    def _del_free_block(self, start, stop):
        del self.free_blocks[start]
        del self.free_blocks_end[stop]
        i = self._get_index(stop - start)
        self.blocks_by_size[i].remove(start)

    def _allocate_block(self, length):
        # First look in the group of index i0 if there is a block that is
        # big enough.  Following an idea found in the Linux malloc.c, we
        # prefer the oldest entries rather than the newest one, to let
        # them have enough time to coalesce into bigger blocks.  It makes
        # a big difference on the purely random test (30% of total usage).
        i0 = self._get_index(length)
        bbs = self.blocks_by_size[i0]
        for j in range(len(bbs)):
            start = bbs[j]
            stop = self.free_blocks[start]
            if start + length <= stop:
                del bbs[j]
                break   # found a block big enough
        else:
            # Then look in the larger groups
            i = i0 + 1
            while i < self.num_indices:
                if len(self.blocks_by_size[i]) > 0:
                    # any block found in a larger group is big enough
                    start = self.blocks_by_size[i].pop(0)
                    stop = self.free_blocks[start]
                    break
                i += 1
            else:
                # Exhausted the memory.  Allocate the resulting block.
                start = self._allocate_large_block(length)
                stop = self.free_blocks[start]
                i = self._get_index(stop - start)
                assert self.blocks_by_size[i][-1] == start
                self.blocks_by_size[i].pop()
        #
        del self.free_blocks[start]
        del self.free_blocks_end[stop]
        return (start, stop)

    def _delete(self):
        "NOT_RPYTHON"
        for data, size in self._allocated:
            rmmap.free(data, size)
