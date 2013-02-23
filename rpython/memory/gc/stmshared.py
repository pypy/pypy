from rpython.rtyper.lltypesystem import lltype, llmemory, llarena
from rpython.rlib.objectmodel import free_non_gc_object

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

    def malloc_object(self, totalsize):
        """Malloc.  You should also call add_regular() later, or keep it in
        some other data structure.  Note that it is not zero-filled."""
        return llarena.arena_malloc(llmemory.raw_malloc_usage(totalsize), 0)

    def add_regular(self, obj):
        """After malloc_object(), register the object in the internal chained
        list.  For objects whose 'revision' field is not otherwise needed."""
        self.gc.set_obj_revision(obj, self.chained_list)
        self.chained_list = obj

    def free_object(self, adr2):
        adr1 = adr2 - self.gc.gcheaderbuilder.size_gc_header
        llarena.arena_free(llarena.getfakearenaaddress(adr1))

    def free_and_clear(self):
        obj = self.chained_list
        self.chained_list = NULL
        while obj:
            next = self.gc.obj_revision(obj)
            self.free_object(obj)
            obj = next

    def free_and_clear_list(self, lst):
        while lst.non_empty():
            self.free_object(lst.pop())

    def delete(self):
        free_non_gc_object(self)
