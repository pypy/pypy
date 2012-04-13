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

    def delete(self):
        self.special_stack.delete()
        free_non_gc_object(self)

    def malloc_regular(self, size):
        """Malloc for an object where the 'version' field can be used
        internally for a chained list."""
        adr1 = llarena.arena_malloc(size, 0)
        adr2 = adr1 + self.gc.gcheaderbuilder
        hdr = llmemory.cast_adr_to_ptr(adr1, lltype.Ptr(self.gc.HDR))
        hdr.version = self.chained_list
        self.chained_list = adr2
        return adr2

    def malloc_special(self, size):
        """Malloc for an object where the 'version' field cannot be
        used internally.  It's the rare case here."""
        adr1 = llarena.arena_malloc(size, 0)
        adr2 = adr1 + self.gc.gcheaderbuilder.size_gc_header
        self.special_stack.append(adr2)
        return adr2

    def free_object(self, adr2):
        adr1 = adr2 - self.gc.gcheaderbuilder.size_gc_header
        llarena.arena_free(adr1)

    def replace_special_stack(self, new_special_stack):
        self.special_stack.delete()
        self.special_stack = new_special_stack
