import sys
from pypy.rlib.rarithmetic import intmask, r_uint, LONG_BIT
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib import rmmap
from pypy.rpython.lltypesystem import lltype, llmemory, rffi


class AsmMemoryManager(object):
    LARGE_ALLOC_SIZE = 1024 * 1024   # 1MB
    MIN_FRAGMENT = 64
    NUM_INDICES = 32     # good for all sizes between 64 bytes and ~490 KB
    _allocated = None

    def __init__(self, large_alloc_size = LARGE_ALLOC_SIZE,
                       min_fragment     = MIN_FRAGMENT,
                       num_indices      = NUM_INDICES):
        self.total_memory_allocated = r_uint(0)
        self.total_mallocs = r_uint(0)
        self.large_alloc_size = large_alloc_size
        self.min_fragment = min_fragment
        self.num_indices = num_indices
        self.free_blocks = {}      # map {start: stop}
        self.free_blocks_end = {}  # map {stop: start}
        self.blocks_by_size = [[] for i in range(self.num_indices)]

    def malloc(self, minsize, maxsize):
        """Allocate executable memory, between minsize and maxsize bytes,
        and return a pair (start, stop).  Does not perform any rounding
        of minsize and maxsize.
        """
        result = self._allocate_block(minsize)
        (start, stop) = result
        smaller_stop = start + maxsize
        if smaller_stop + self.min_fragment <= stop:
            self._add_free_block(smaller_stop, stop)
            stop = smaller_stop
            result = (start, stop)
        self.total_mallocs += stop - start
        return result   # pair (start, stop)

    def free(self, start, stop):
        """Free a block (start, stop) returned by a previous malloc()."""
        self.total_mallocs -= (stop - start)
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
            if self._allocated is None:
                self._allocated = []
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
        if self._allocated:
            for data, size in self._allocated:
                rmmap.free(data, size)
        self._allocated = None


class BlockBuilderMixin(object):
    _mixin_ = True
    # A base class to generate assembler.  It is equivalent to just a list
    # of chars, but it is potentially more efficient for that usage.
    # It works by allocating the assembler SUBBLOCK_SIZE bytes at a time.
    # Ideally, this number should be a power of two that fits the GC's most
    # compact allocation scheme (which is so far 35 * WORD for minimark.py).
    WORD = LONG_BIT // 8
    SUBBLOCK_SIZE = 32 * WORD
    SUBBLOCK_PTR = lltype.Ptr(lltype.GcForwardReference())
    SUBBLOCK = lltype.GcStruct('SUBBLOCK',
                   ('prev', SUBBLOCK_PTR),
                   ('data', lltype.FixedSizeArray(lltype.Char, SUBBLOCK_SIZE)))
    SUBBLOCK_PTR.TO.become(SUBBLOCK)

    gcroot_markers = None
    gcroot_markers_total_size = 0

    def __init__(self, translated=None):
        if translated is None:
            translated = we_are_translated()
        if translated:
            self.init_block_builder()
        else:
            self._become_a_plain_block_builder()

    def init_block_builder(self):
        self._cursubblock = lltype.nullptr(self.SUBBLOCK)
        self._baserelpos = -self.SUBBLOCK_SIZE
        self._make_new_subblock()

    def _make_new_subblock(self):
        nextsubblock = lltype.malloc(self.SUBBLOCK)
        nextsubblock.prev = self._cursubblock
        self._cursubblock = nextsubblock
        self._cursubindex = 0
        self._baserelpos += self.SUBBLOCK_SIZE
    _make_new_subblock._dont_inline_ = True

    def writechar(self, char):
        index = self._cursubindex
        if index == self.SUBBLOCK_SIZE:
            self._make_new_subblock()
            index = 0
        self._cursubblock.data[index] = char
        self._cursubindex = index + 1

    def overwrite(self, index, char):
        assert 0 <= index < self.get_relative_pos()
        block = self._cursubblock
        index -= self._baserelpos
        while index < 0:
            block = block.prev
            index += self.SUBBLOCK_SIZE
        block.data[index] = char

    def get_relative_pos(self):
        return self._baserelpos + self._cursubindex

    def copy_to_raw_memory(self, addr):
        # indirection for _become_a_plain_block_builder() and for subclasses
        self._copy_to_raw_memory(addr)

    def _copy_to_raw_memory(self, addr):
        block = self._cursubblock
        blocksize = self._cursubindex
        targetindex = self._baserelpos
        while targetindex >= 0:
            dst = rffi.cast(rffi.CCHARP, addr + targetindex)
            for j in range(blocksize):
                dst[j] = block.data[j]
            block = block.prev
            blocksize = self.SUBBLOCK_SIZE
            targetindex -= self.SUBBLOCK_SIZE
        assert not block

    def materialize(self, asmmemmgr, allblocks, gcrootmap=None):
        size = self.get_relative_pos()
        malloced = asmmemmgr.malloc(size, size)
        allblocks.append(malloced)
        rawstart = malloced[0]
        self.copy_to_raw_memory(rawstart)
        if self.gcroot_markers is not None:
            assert gcrootmap is not None
            gcrootmap.add_raw_gcroot_markers(asmmemmgr,
                                             allblocks,
                                             self.gcroot_markers,
                                             self.gcroot_markers_total_size,
                                             rawstart)
        return rawstart

    def _become_a_plain_block_builder(self):
        # hack purely for speed of tests
        self._data = []
        self.writechar = self._data.append
        self.overwrite = self._data.__setitem__
        self.get_relative_pos = self._data.__len__
        def plain_copy_to_raw_memory(addr):
            dst = rffi.cast(rffi.CCHARP, addr)
            for i, c in enumerate(self._data):
                dst[i] = c
        self._copy_to_raw_memory = plain_copy_to_raw_memory

    def insert_gcroot_marker(self, mark):
        if self.gcroot_markers is None:
            self.gcroot_markers = []
        self.gcroot_markers.append((self.get_relative_pos(), mark))
        self.gcroot_markers_total_size += len(mark)
