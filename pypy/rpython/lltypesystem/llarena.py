import array
from pypy.rpython.lltypesystem import lltype, llmemory

# An "arena" is a large area of memory which can hold a number of
# objects, not necessarily all of the same type or size.  It's used by
# some of our framework GCs.  Addresses that point inside arenas support
# direct arithmetic: adding and subtracting integers, and taking the
# difference of two addresses.  When not translated to C, the arena
# keeps track of which bytes are used by what object to detect GC bugs;
# it internally uses raw_malloc_usage() to estimate the number of bytes
# it needs to reserve.

class ArenaError(Exception):
    pass

class Arena(object):
    object_arena_location = {}     # {container: (arena, offset)}

    def __init__(self, nbytes, zero):
        self.nbytes = nbytes
        self.usagemap = array.array('c')
        self.objectptrs = {}        # {offset: ptr-to-container}
        self.objectsizes = {}       # {offset: size}
        self.freed = False
        self.reset(zero)

    def reset(self, zero):
        self.check()
        for ptr in self.objectptrs.itervalues():
            obj = ptr._obj
            obj._free()
            del Arena.object_arena_location[obj]
        self.objectptrs.clear()
        self.objectsizes.clear()
        if zero:
            initialbyte = "0"
        else:
            initialbyte = "#"
        self.usagemap[:] = array.array('c', initialbyte * self.nbytes)

    def check(self):
        if self.freed:
            raise ArenaError("arena was already freed")

    def _getid(self):
        address, length = self.usagemap.buffer_info()
        return address

    def getaddr(self, offset):
        if not (0 <= offset <= self.nbytes):
            raise ArenaError("Address offset is outside the arena")
        return fakearenaaddress(self, offset)

    def allocate_object(self, offset, size):
        self.check()
        bytes = llmemory.raw_malloc_usage(size)
        if offset + bytes > self.nbytes:
            raise ArenaError("object overflows beyond the end of the arena")
        zero = True
        for c in self.usagemap[offset:offset+bytes]:
            if c == '0':
                pass
            elif c == '#':
                zero = False
            else:
                raise ArenaError("new object overlaps a previous object")
        assert offset not in self.objectptrs
        addr2 = size._raw_malloc([], zero=zero)
        pattern = 'X' + 'x'*(bytes-1)
        self.usagemap[offset:offset+bytes] = array.array('c', pattern)
        self.objectptrs[offset] = addr2.ptr
        self.objectsizes[offset] = bytes
        Arena.object_arena_location[addr2.ptr._obj] = self, offset
        # common case: 'size' starts with a GCHeaderOffset.  In this case
        # we can also remember that the real object starts after the header.
        if (isinstance(size, llmemory.CompositeOffset) and
            isinstance(size.offsets[0], llmemory.GCHeaderOffset)):
            objaddr = addr2 + size.offsets[0]
            hdrbytes = llmemory.raw_malloc_usage(size.offsets[0])
            objoffset = offset + hdrbytes
            assert objoffset not in self.objectptrs
            self.objectptrs[objoffset] = objaddr.ptr
            self.objectsizes[objoffset] = bytes - hdrbytes
            Arena.object_arena_location[objaddr.ptr._obj] = self, objoffset
        return addr2

class fakearenaaddress(llmemory.fakeaddress):

    def __init__(self, arena, offset):
        self.arena = arena
        self.offset = offset

    def _getptr(self):
        try:
            return self.arena.objectptrs[self.offset]
        except KeyError:
            self.arena.check()
            raise ArenaError("don't know yet what type of object "
                             "is at offset %d" % (self.offset,))
    ptr = property(_getptr)

    def __repr__(self):
        return '<arenaaddr %s + %d>' % (self.arena, self.offset)

    def __add__(self, other):
        if isinstance(other, (int, long)):
            position = self.offset + other
        elif isinstance(other, llmemory.AddressOffset):
            # this is really some Do What I Mean logic.  There are two
            # possible meanings: either we want to go past the current
            # object in the arena, or we want to take the address inside
            # the current object.  Try to guess...
            bytes = llmemory.raw_malloc_usage(other)
            if (self.offset in self.arena.objectsizes and
                bytes < self.arena.objectsizes[self.offset]):
                # looks like we mean "inside the object"
                return llmemory.fakeaddress.__add__(self, other)
            position = self.offset + bytes
        else:
            return NotImplemented
        return self.arena.getaddr(position)

    def __sub__(self, other):
        if isinstance(other, llmemory.AddressOffset):
            other = llmemory.raw_malloc_usage(other)
        if isinstance(other, (int, long)):
            return self.arena.getaddr(self.offset - other)
        if isinstance(other, fakearenaaddress):
            if self.arena is not other.arena:
                raise ArenaError("The two addresses are from different arenas")
            return self.offset - other.offset
        return NotImplemented

    def __nonzero__(self):
        return True

    def __eq__(self, other):
        if isinstance(other, fakearenaaddress):
            return self.arena is other.arena and self.offset == other.offset
        elif isinstance(other, llmemory.fakeaddress):
            if other.ptr and other.ptr._obj in Arena.object_arena_location:
                arena, offset = Arena.object_arena_location[other.ptr._obj]
                return self.arena is arena and self.offset == offset
            else:
                return False
        else:
            return llmemory.fakeaddress.__eq__(self, other)

    def __lt__(self, other):
        if isinstance(other, fakearenaaddress):
            arena = other.arena
            offset = other.offset
        elif isinstance(other, llmemory.fakeaddress):
            if other.ptr and other.ptr._obj in Arena.object_arena_location:
                arena, offset = Arena.object_arena_location[other.ptr._obj]
            else:
                # arbitrarily, 'self' > any address not in any arena
                return False
        else:
            raise TypeError("comparing a %s and a %s" % (
                self.__class__.__name__, other.__class__.__name__))
        if self.arena is arena:
            return self.offset < offset
        else:
            return self.arena._getid() < arena._getid()

    def _cast_to_int(self):
        return self.arena._getid() + self.offset

# ____________________________________________________________
#
# Public interface: arena_malloc(), arena_free() and arena_reset()
# which directly correspond to lloperations.  Although the operations
# are similar to raw_malloc(), raw_free() and raw_memclear(), the
# backend can choose a different implementation for arenas, one that
# is more suited to very large chunks of memory.

def arena_malloc(nbytes, zero):
    """Allocate and return a new arena, optionally zero-initialized."""
    return Arena(nbytes, zero).getaddr(0)

def arena_free(arena_addr):
    """Release an arena."""
    assert isinstance(arena_addr, fakearenaaddress)
    assert arena_addr.offset == 0
    arena_addr.arena.reset(False)
    arena_addr.arena.freed = True

def arena_reset(arena_addr, myarenasize, zero):
    """Free all objects in the arena, which can then be reused.
    The arena is filled with zeroes if 'zero' is True."""
    assert isinstance(arena_addr, fakearenaaddress)
    assert arena_addr.offset == 0
    assert myarenasize == arena_addr.arena.nbytes
    arena_addr.arena.reset(zero)

def arena_reserve(addr, size):
    """Mark some bytes in an arena as reserved, and returns addr.
    For debugging this can check that reserved ranges of bytes don't
    overlap.  The size must be symbolic; in non-translated version
    this is used to know what type of lltype object to allocate."""
    assert isinstance(addr, fakearenaaddress)
    addr.arena.allocate_object(addr.offset, size)
