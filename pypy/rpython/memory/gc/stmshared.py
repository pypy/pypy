from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rlib.objectmodel import free_non_gc_object

NULL = llmemory.NULL


class StmGCSharedArea(object):
    _alloc_flavor_ = 'raw'

    def __init__(self, gc):
        self.gc = gc

    def setup(self):
        pass


class StmGCThreadLocalAllocator(object):
    """A thread-local allocator for the shared area.
    This is an optimization only: it lets us use thread-local variables
    to keep track of what we allocated.
    """
    _alloc_flavor_ = 'raw'

    def __init__(self, sharedarea):
        self.gc = sharedarea.gc
        self.sharedarea = sharedarea
        self.chained_list = NULL
        self.special_stack = self.gc.AddressStack()

    def malloc_object(self, totalsize):
        """Malloc.  You must also call add_regular() or add_special() later."""
        adr1 = llarena.arena_malloc(llmemory.raw_malloc_usage(totalsize), 0)
        llarena.arena_reserve(adr1, totalsize)
        return adr1 + self.gc.gcheaderbuilder.size_gc_header

    def add_regular(self, obj):
        """After malloc_object(), register the object in the internal chained
        list.  For objects whose 'version' field is not otherwise needed."""
        hdr = self.gc.header(obj)
        hdr.version = self.chained_list
        self.chained_list = obj

    def add_special(self, obj):
        """After malloc_object(), register the object in a separate stack."""
        self.special_stack.append(obj)

    def free_object(self, adr2):
        adr1 = adr2 - self.gc.gcheaderbuilder.size_gc_header
        llarena.arena_free(llarena.getfakearenaaddress(adr1))

    def clear(self):
        obj = self.chained_list
        self.chained_list = NULL
        while obj:
            next = self.gc.header(obj).version
            self.free_object(obj)
            obj = next
        s = self.special_stack
        while s.non_empty():
            self.free_object(s.pop())

    def delete(self):
        self.special_stack.delete()
        free_non_gc_object(self)
