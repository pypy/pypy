import sys
from pypy.rpython.memory.gc.semispace import SemiSpaceGC
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rlib.objectmodel import free_non_gc_object, debug_assert

nonnull_endmarker = llmemory.raw_malloc(llmemory.sizeof(lltype.Char))
llmemory.raw_memclear(nonnull_endmarker, llmemory.sizeof(lltype.Char))


class GenerationGC(SemiSpaceGC):
    """A basic generational GC: it's a SemiSpaceGC with an additional
    nursery for young objects.  A write barrier is used to ensure that
    old objects that contain pointers to young objects are in a linked
    list, chained to each other via their 'forw' header field.
    """
    inline_simple_malloc = True

    def __init__(self, AddressLinkedList,
                 nursery_size=128,
                 space_size=4096,
                 max_space_size=sys.maxint//2+1,
                 get_roots=None):
        SemiSpaceGC.__init__(self, AddressLinkedList,
                             space_size = space_size,
                             max_space_size = max_space_size,
                             get_roots = get_roots)
        self.nursery_size = nursery_size

    def setup(self):
        SemiSpaceGC.setup(self)
        self.nursery = llarena.arena_malloc(self.nursery_size, True)
        debug_assert(bool(self.nursery), "couldn't allocate nursery")
        self.nursery_free = self.nursery
        self.nursery_top = self.nursery + self.nursery_size
        self.old_objects_pointing_to_young = nonnull_endmarker
        # ^^^ the head of a linked list inside the old objects space

    def is_in_nursery(self, addr):
        return self.nursery <= addr < self.nursery_top

    def malloc_fixedsize(self, typeid, size, can_collect, has_finalizer=False,
                         contains_weakptr=False):
        if (has_finalizer or contains_weakptr or not can_collect or
            raw_malloc_usage(size) >= self.nursery_size // 2):
            # "non-simple" case or object too big: don't use the nursery
            return SemiSpaceGC.malloc_fixedsize(self, typeid, size,
                                                can_collect, has_finalizer,
                                                contains_weakptr)
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self.nursery_free
        if raw_malloc_usage(totalsize) > self.nursery_top - result:
            result = self.collect_nursery()
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid)
        self.nursery_free = result + totalsize
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    def semispace_collect(self, size_changing=False):
        self.reset_forwarding() # we are doing a full collection anyway
        SemiSpaceGC.semispace_collect(self, size_changing)

    def reset_forwarding(self):
        obj = self.old_objects_pointing_to_young
        while obj != nonnull_endmarker:
            hdr = self.header(obj)
            obj = hdr.forw
            hdr.forw = llmemory.NULL
        self.old_objects_pointing_to_young = nonnull_endmarker

    def collect_nursery(self):
        if self.nursery_size > self.top_of_space - self.free:
            # the semispace is running out, do a full collect
            self.obtain_free_space(self.nursery_size)
            debug_assert(self.nursery_free == self.nursery,
                         "nursery not collected")
        else:
            scan = self.free
            self.collect_oldrefs_to_nursery()
            self.collect_roots_in_nursery()
            self.scan_objects_just_copied_out_of_nursery(scan)
            self.notify_objects_just_moved()
        return self.nursery_free

    def reset_nursery(self):
        llarena.arena_reset(self.nursery, self.nursery_size, True)
        self.nursery_free = self.nursery

    def notify_objects_just_moved(self):
        self.reset_nursery()
        SemiSpaceGC.notify_objects_just_moved(self)

    # NB. we can use self.copy() to move objects out of the nursery,
    # but only if the object was really in the nursery.

    def collect_oldrefs_to_nursery(self):
        # Follow the old_objects_pointing_to_young list and move the
        # young objects they point to out of the nursery.  The 'forw'
        # fields are reset to NULL along the way.
        obj = self.old_objects_pointing_to_young
        while obj != nonnull_endmarker:
            self.trace_and_drag_out_of_nursery(obj)
            hdr = self.header(obj)
            obj = hdr.forw
            hdr.forw = llmemory.NULL
        self.old_objects_pointing_to_young = nonnull_endmarker

    def collect_roots_in_nursery(self):
        roots = self.get_roots()
        while 1:
            root = roots.pop()
            if root == NULL:
                break
            obj = root.address[0]
            if self.is_in_nursery(obj):
                root.address[0] = self.copy(obj)
        free_non_gc_object(roots)

    def scan_objects_just_copied_out_of_nursery(self, scan):
        while scan < self.free:
            curr = scan + self.size_gc_header()
            self.trace_and_drag_out_of_nursery(curr)
            scan += self.size_gc_header() + self.get_size(curr)
        return scan

    def trace_and_drag_out_of_nursery(self, obj):
        """obj must not be in the nursery.  This copies all the
        young objects it references out of the nursery.
        """
        gc_info = self.header(obj)
        typeid = gc_info.typeid
        offsets = self.offsets_to_gc_pointers(typeid)
        i = 0
        while i < len(offsets):
            pointer = obj + offsets[i]
            if self.is_in_nursery(pointer.address[0]):
                pointer.address[0] = self.copy(pointer.address[0])
            i += 1
        if self.is_varsize(typeid):
            offset = self.varsize_offset_to_variable_part(
                typeid)
            length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
            offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
            itemlength = self.varsize_item_sizes(typeid)
            i = 0
            while i < length:
                item = obj + offset + itemlength * i
                j = 0
                while j < len(offsets):
                    pointer = item + offsets[j]
                    if self.is_in_nursery(pointer.address[0]):
                        pointer.address[0] = self.copy(pointer.address[0])
                    j += 1
                i += 1

    def write_barrier(self, addr, addr_to, addr_struct):
        if not self.is_in_nursery(addr_struct) and self.is_in_nursery(addr):
            oldhdr = self.header(addr_struct)
            if oldhdr.forw == NULL:
                oldhdr.forw = self.old_objects_pointing_to_young
                self.old_objects_pointing_to_young = addr_struct
        addr_to.address[0] = addr
