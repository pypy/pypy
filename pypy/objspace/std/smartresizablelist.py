# implement resizable arrays
# see "Resizable Arrays in Optimal time and Space"
# Brodnik, Carlsson, Demaine, Munro, Sedgewick, 1999

from pypy.objspace.std.listmultiobject import ListImplementation
import sys
import math
LOG2 = math.log(2)
NBITS = int(math.log(sys.maxint) / LOG2) + 2
LSBSTEPS = int(math.log(NBITS) / LOG2) + 1

def leftmost_set_bit(i):
    # return int(math.log(i) / LOG2)
    # do something fancy?
    assert i > 0
    shift = NBITS // 2
    result = 0
    for x in range(LSBSTEPS):
        newi = i >> shift
        if newi:
            result += shift
            i = newi
        shift //= 2
    return result

def decompose(i, k):
    halfk_lower = k // 2
    halfk_upper = halfk_lower + (k & 1)
    mask1 = ((1 << halfk_lower) - 1)  << halfk_upper 
    mask2 = ((1 << halfk_upper) - 1)
    assert mask1 + mask2 == ((1 << k) - 1)
    return ((i & mask1) >> halfk_upper), i & mask2

def find_block_index(i):
    if i == 0:
        return (0, 0)
    k = leftmost_set_bit(i + 1)
    b, e = decompose(i + 1, k)
    x = k
    m =  (1 << (x // 2 + 1)) - 2 + (x & 1) * (1 << (x // 2))
    return m + b, e

class FreeList(object):
    def __init__(self):
        self.freelist = {}

    def alloc(self, size):
        l = self.freelist.get(size, None)
        if l is not None and l:
            return l.pop()
        return [None] * size

    def dealloc(self, l):
        size = len(l)
        if size >= 2 ** 20:
            return
        if size in self.freelist:
            self.freelist[size].append(l)
        else:
            self.freelist[size] = [l]

freelist = FreeList()

class SmartResizableListImplementation(ListImplementation):
    def __init__(self, space):
        self._length = 0
        self.size_superblock = 1
        self.size_datablock = 1
        self.num_superblocks = 1 # "s" in the paper
        self.num_datablocks = 1 # "d" in the paper
        self.last_superblock_filled = 1
        self.index_last = 0 # number of elements occupying last data block
        self.data_blocks = [[None] * 1]
        self.space = space

    def length(self):
        return self._length
   
    def grow(self, items=1):
        data_blocks = self.data_blocks
        self._length += items
        idx = self.num_datablocks - 1
        assert idx >= 0
        free_in_last_datablock = len(data_blocks[idx]) - self.index_last
        while items > free_in_last_datablock:
            items -= free_in_last_datablock
            free_in_last_datablock = self.grow_block()
        self.index_last += items
        return (self.num_datablocks - 1, self.index_last - 1)

    def grow_block(self):
        data_blocks = self.data_blocks
        if self.last_superblock_filled == self.size_superblock:
            self.num_superblocks += 1
            if self.num_superblocks % 2 == 1:
                self.size_superblock *= 2
            else:
                self.size_datablock *= 2
            self.last_superblock_filled = 0
        if len(data_blocks) == self.num_datablocks:
            data_blocks.append(freelist.alloc(self.size_datablock))
        self.last_superblock_filled += 1
        self.num_datablocks += 1
        self.index_last = 0
        return self.size_datablock

    def shrink(self, items=1):
        if items > self._length:
            raise ValueError("cannot shrink by more items than the list has")
        self._length -= items
        data_blocks = self.data_blocks
        while items > self.index_last:
            items -= self.index_last
            self.shrink_block()
        self.index_last -= items
        idx = self.num_datablocks - 1
        assert idx >= 0
        data_block = data_blocks[idx]
        while items:
            idx = self.index_last - 1 + items
            assert idx >= 0
            data_block[idx] = None
            items -= 1

    def shrink_block(self):
        data_blocks = self.data_blocks
        if len(data_blocks) > self.num_datablocks:
            assert len(data_blocks) - self.num_datablocks == 1
            freelist.dealloc(data_blocks.pop())
        for i in range(self.index_last): #XXX consider when not to do this
            idx = self.num_datablocks - 1
            assert idx >= 0
            data_blocks[idx][i] = None
        self.num_datablocks -= 1
        self.last_superblock_filled -= 1
        if self.last_superblock_filled == 0:
            self.num_superblocks -= 1
            if self.num_superblocks % 2 == 0:
                self.size_superblock //= 2
            else:
                self.size_datablock //= 2
            self.last_superblock_filled = self.size_superblock
        self.index_last = len(data_blocks[-2])

    def getitem(self, i):
        a, b = find_block_index(i)
        return self.getitem_raw(a, b)

    def getitem_raw(self, a, b):
        assert a >= 0
        assert b >= 0
        return self.data_blocks[a][b]

    def setitem(self, i, value):
        a, b = find_block_index(i)
        return self.setitem_raw(a, b, value)

    def setitem_raw(self, a, b, value):
        assert a >= 0
        assert b >= 0
        self.data_blocks[a][b] = value

    def getitem_slice(self, start, stop):
        l = stop - start
        result = SmartResizableListImplementation(self.space)
        result.grow(l)
        for i in range(l):
            result.setitem(i, self.getitem(i + start))
        return result

    def insert(self, i, w_item):
        self.grow()
        for x in range(self._length - 2, i - 1, -1):
            self.setitem(x + 1, self.getitem(x))
        self.setitem(i, w_item)
        return self

    def delitem(self, index):
        for x in range(index + 1, self._length):
            self.setitem(x - 1, self.getitem(x))
        self.shrink()
        return self

    def delitem_slice(self, start, stop):
        slicelength = stop - start
        for x in range(stop, self._length):
            self.setitem(x - slicelength, self.getitem(x))
        self.shrink(slicelength)
        return self

    def append(self, w_item):
        a, b = self.grow()
        self.setitem_raw(a, b, w_item)
        return self

    def extend(self, other):
        selflength = self._length
        length = other.length()
        self.grow(length)
        for i in range(length):
            self.setitem(selflength + i, other.getitem(i))
        return self

# special cases:

    def add(self, other):
        result = self.copy()
        result.extend(other)
        return result

    def get_list_w(self):
        l = self._length
        result = [None] * l
        for i in range(l):
            result[i] = self.getitem(i)
        return result

# default implementations, can (but don't have to be) overridden:

    def copy(self):
        from pypy.rlib.objectmodel import instantiate
        result = instantiate(SmartResizableListImplementation)
        result._length = self._length
        result.size_superblock = self.size_superblock
        result.size_datablock = self.size_datablock
        result.num_superblocks = self.num_superblocks
        result.num_datablocks = self.num_datablocks
        result.last_superblock_filled = self.last_superblock_filled
        result.index_last = self.index_last
        result.data_blocks = [l[:] for l in self.data_blocks]
        result.space = self.space
        return result
