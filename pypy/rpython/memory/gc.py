from pypy.rpython.lltypesystem.llmemory import raw_malloc, raw_free
from pypy.rpython.lltypesystem.llmemory import raw_memcopy, raw_memclear
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rpython.memory.support import get_address_linked_list
from pypy.rpython.memory.gcheader import GCHeaderBuilder
from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rlib.objectmodel import free_non_gc_object, debug_assert
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.rarithmetic import ovfcheck

import sys, os

X_POOL = lltype.GcOpaqueType('gc.pool')
X_POOL_PTR = lltype.Ptr(X_POOL)
X_CLONE = lltype.GcStruct('CloneData', ('gcobjectptr', llmemory.GCREF),
                                       ('pool',        X_POOL_PTR))
X_CLONE_PTR = lltype.Ptr(X_CLONE)


class GCBase(object):
    _alloc_flavor_ = "raw"
    moving_gc = False

    def set_query_functions(self, is_varsize, getfinalizer,
                            offsets_to_gc_pointers,
                            fixed_size, varsize_item_sizes,
                            varsize_offset_to_variable_part,
                            varsize_offset_to_length,
                            varsize_offsets_to_gcpointers_in_var_part,
                            weakpointer_offset):
        self.getfinalizer = getfinalizer
        self.is_varsize = is_varsize
        self.offsets_to_gc_pointers = offsets_to_gc_pointers
        self.fixed_size = fixed_size
        self.varsize_item_sizes = varsize_item_sizes
        self.varsize_offset_to_variable_part = varsize_offset_to_variable_part
        self.varsize_offset_to_length = varsize_offset_to_length
        self.varsize_offsets_to_gcpointers_in_var_part = varsize_offsets_to_gcpointers_in_var_part
        self.weakpointer_offset = weakpointer_offset

    def write_barrier(self, addr, addr_to, addr_struct):
        addr_to.address[0] = addr

    def setup(self):
        pass

    def statistics(self, index):
        return -1

    def size_gc_header(self, typeid=0):
        return self.gcheaderbuilder.size_gc_header

    def malloc(self, typeid, length=0, zero=False):
        """For testing.  The interface used by the gctransformer is
        the four malloc_[fixed,var]size[_clear]() functions.
        """
        size = self.fixed_size(typeid)
        needs_finalizer = bool(self.getfinalizer(typeid))
        weakptr_offset = self.weakpointer_offset(typeid)
        #XXX cannot compare weakptr_offset with -1
        #contains_weakptr = weakpointer_offset. != -1
        if isinstance(weakptr_offset, int):
            assert weakptr_offset == -1
            contains_weakptr = False
        else:
            contains_weakptr = True
        assert not (needs_finalizer and contains_weakptr)
        if self.is_varsize(typeid):
            assert not contains_weakptr
            itemsize = self.varsize_item_sizes(typeid)
            offset_to_length = self.varsize_offset_to_length(typeid)
            if zero:
                malloc_varsize = self.malloc_varsize_clear
            else:
                malloc_varsize = self.malloc_varsize
            ref = malloc_varsize(typeid, length, size, itemsize,
                                 offset_to_length, True, needs_finalizer)
        else:
            if zero:
                malloc_fixedsize = self.malloc_fixedsize_clear
            else:
                malloc_fixedsize = self.malloc_fixedsize
            ref = malloc_fixedsize(typeid, size, True, needs_finalizer,
                                   contains_weakptr)
        # lots of cast and reverse-cast around...
        return llmemory.cast_ptr_to_adr(ref)

    def x_swap_pool(self, newpool):
        return newpool

    def x_clone(self, clonedata):
        raise RuntimeError("no support for x_clone in the GC")

    def x_become(self, target_addr, source_addr):
        raise RuntimeError("no support for x_become in the GC")


DEBUG_PRINT = False
memoryError = MemoryError()
class MarkSweepGC(GCBase):
    _alloc_flavor_ = "raw"

    HDR = lltype.ForwardReference()
    HDRPTR = lltype.Ptr(HDR)
    # need to maintain a linked list of malloced objects, since we used the
    # systems allocator and can't walk the heap
    HDR.become(lltype.Struct('header', ('typeid', lltype.Signed),
                                       ('next', HDRPTR)))

    POOL = lltype.GcStruct('gc_pool')
    POOLPTR = lltype.Ptr(POOL)

    POOLNODE = lltype.ForwardReference()
    POOLNODEPTR = lltype.Ptr(POOLNODE)
    POOLNODE.become(lltype.Struct('gc_pool_node', ('linkedlist', HDRPTR),
                                                  ('nextnode', POOLNODEPTR)))

    def __init__(self, AddressLinkedList, start_heap_size=4096, get_roots=None):
        self.heap_usage = 0          # at the end of the latest collection
        self.bytes_malloced = 0      # since the latest collection
        self.bytes_malloced_threshold = start_heap_size
        self.total_collection_time = 0.0
        self.AddressLinkedList = AddressLinkedList
        self.malloced_objects = lltype.nullptr(self.HDR)
        self.malloced_objects_with_finalizer = lltype.nullptr(self.HDR)
        # these are usually only the small bits of memory that make a
        # weakref object
        self.objects_with_weak_pointers = lltype.nullptr(self.HDR)
        self.get_roots = get_roots
        self.gcheaderbuilder = GCHeaderBuilder(self.HDR)
        # pools, for x_swap_pool():
        #   'curpool' is the current pool, lazily allocated (i.e. NULL means
        #   the current POOL object is not yet malloc'ed).  POOL objects are
        #   usually at the start of a linked list of objects, via the HDRs.
        #   The exception is 'curpool' whose linked list of objects is in
        #   'self.malloced_objects' instead of in the header of 'curpool'.
        #   POOL objects are never in the middle of a linked list themselves.
        # XXX a likely cause for the current problems with pools is:
        # not all objects live in malloced_objects, some also live in
        # malloced_objects_with_finalizer and objects_with_weak_pointers
        self.curpool = lltype.nullptr(self.POOL)
        #   'poolnodes' is a linked list of all such linked lists.  Each
        #   linked list will usually start with a POOL object, but it can
        #   also contain only normal objects if the POOL object at the head
        #   was already freed.  The objects in 'malloced_objects' are not
        #   found via 'poolnodes'.
        self.poolnodes = lltype.nullptr(self.POOLNODE)
        self.collect_in_progress = False
        self.prev_collect_end_time = 0.0

    def malloc_fixedsize(self, typeid, size, can_collect, has_finalizer=False,
                         contains_weakptr=False):
        if can_collect and self.bytes_malloced > self.bytes_malloced_threshold:
            self.collect()
        size_gc_header = self.gcheaderbuilder.size_gc_header
        try:
            tot_size = size_gc_header + size
            usage = raw_malloc_usage(tot_size)
            bytes_malloced = ovfcheck(self.bytes_malloced+usage)
            ovfcheck(self.heap_usage + bytes_malloced)
        except OverflowError:
            raise memoryError
        result = raw_malloc(tot_size)
        if not result:
            raise memoryError
        hdr = llmemory.cast_adr_to_ptr(result, self.HDRPTR)
        hdr.typeid = typeid << 1
        if has_finalizer:
            hdr.next = self.malloced_objects_with_finalizer
            self.malloced_objects_with_finalizer = hdr
        elif contains_weakptr:
            hdr.next = self.objects_with_weak_pointers
            self.objects_with_weak_pointers = hdr
        else:
            hdr.next = self.malloced_objects
            self.malloced_objects = hdr
        self.bytes_malloced = bytes_malloced
        result += size_gc_header
        #llop.debug_print(lltype.Void, 'malloc typeid', typeid,
        #                 '->', llmemory.cast_adr_to_int(result))
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)

    def malloc_fixedsize_clear(self, typeid, size, can_collect,
                               has_finalizer=False, contains_weakptr=False):
        if can_collect and self.bytes_malloced > self.bytes_malloced_threshold:
            self.collect()
        size_gc_header = self.gcheaderbuilder.size_gc_header
        try:
            tot_size = size_gc_header + size
            usage = raw_malloc_usage(tot_size)
            bytes_malloced = ovfcheck(self.bytes_malloced+usage)
            ovfcheck(self.heap_usage + bytes_malloced)
        except OverflowError:
            raise memoryError
        result = raw_malloc(tot_size)
        if not result:
            raise memoryError
        raw_memclear(result, tot_size)
        hdr = llmemory.cast_adr_to_ptr(result, self.HDRPTR)
        hdr.typeid = typeid << 1
        if has_finalizer:
            hdr.next = self.malloced_objects_with_finalizer
            self.malloced_objects_with_finalizer = hdr
        elif contains_weakptr:
            hdr.next = self.objects_with_weak_pointers
            self.objects_with_weak_pointers = hdr
        else:
            hdr.next = self.malloced_objects
            self.malloced_objects = hdr
        self.bytes_malloced = bytes_malloced
        result += size_gc_header
        #llop.debug_print(lltype.Void, 'malloc typeid', typeid,
        #                 '->', llmemory.cast_adr_to_int(result))
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)

    def malloc_varsize(self, typeid, length, size, itemsize, offset_to_length,
                       can_collect, has_finalizer=False):
        if can_collect and self.bytes_malloced > self.bytes_malloced_threshold:
            self.collect()
        size_gc_header = self.gcheaderbuilder.size_gc_header
        try:
            fixsize = size_gc_header + size
            varsize = ovfcheck(itemsize * length)
            tot_size = ovfcheck(fixsize + varsize)
            usage = raw_malloc_usage(tot_size)
            bytes_malloced = ovfcheck(self.bytes_malloced+usage)
            ovfcheck(self.heap_usage + bytes_malloced)
        except OverflowError:
            raise memoryError
        result = raw_malloc(tot_size)
        if not result:
            raise memoryError
        (result + size_gc_header + offset_to_length).signed[0] = length
        hdr = llmemory.cast_adr_to_ptr(result, self.HDRPTR)
        hdr.typeid = typeid << 1
        if has_finalizer:
            hdr.next = self.malloced_objects_with_finalizer
            self.malloced_objects_with_finalizer = hdr
        else:
            hdr.next = self.malloced_objects
            self.malloced_objects = hdr
        self.bytes_malloced = bytes_malloced
            
        result += size_gc_header
        #llop.debug_print(lltype.Void, 'malloc_varsize length', length,
        #                 'typeid', typeid,
        #                 '->', llmemory.cast_adr_to_int(result))
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)

    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length, can_collect,
                             has_finalizer=False):
        if can_collect and self.bytes_malloced > self.bytes_malloced_threshold:
            self.collect()
        size_gc_header = self.gcheaderbuilder.size_gc_header
        try:
            fixsize = size_gc_header + size
            varsize = ovfcheck(itemsize * length)
            tot_size = ovfcheck(fixsize + varsize)
            usage = raw_malloc_usage(tot_size)
            bytes_malloced = ovfcheck(self.bytes_malloced+usage)
            ovfcheck(self.heap_usage + bytes_malloced)
        except OverflowError:
            raise memoryError
        result = raw_malloc(tot_size)
        if not result:
            raise memoryError
        raw_memclear(result, tot_size)        
        (result + size_gc_header + offset_to_length).signed[0] = length
        hdr = llmemory.cast_adr_to_ptr(result, self.HDRPTR)
        hdr.typeid = typeid << 1
        if has_finalizer:
            hdr.next = self.malloced_objects_with_finalizer
            self.malloced_objects_with_finalizer = hdr
        else:
            hdr.next = self.malloced_objects
            self.malloced_objects = hdr
        self.bytes_malloced = bytes_malloced
            
        result += size_gc_header
        #llop.debug_print(lltype.Void, 'malloc_varsize length', length,
        #                 'typeid', typeid,
        #                 '->', llmemory.cast_adr_to_int(result))
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)

    def collect(self):
        # 1. mark from the roots, and also the objects that objects-with-del
        #    point to (using the list of malloced_objects_with_finalizer)
        # 2. walk the list of objects-without-del and free the ones not marked
        # 3. walk the list of objects-with-del and for the ones not marked:
        #    call __del__, move the object to the list of object-without-del
        import time
        from pypy.rpython.lltypesystem.lloperation import llop
        if DEBUG_PRINT:
            llop.debug_print(lltype.Void, 'collecting...')
        start_time = time.time()
        self.collect_in_progress = True
        roots = self.get_roots()
        size_gc_header = self.gcheaderbuilder.size_gc_header
##        llop.debug_view(lltype.Void, self.malloced_objects, self.poolnodes,
##                        size_gc_header)

        # push the roots on the mark stack
        objects = self.AddressLinkedList() # mark stack
        while 1:
            curr = roots.pop()
            if curr == NULL:
                break
            # roots is a list of addresses to addresses:
            objects.append(curr.address[0])
        free_non_gc_object(roots)
        # from this point onwards, no more mallocs should be possible
        old_malloced = self.bytes_malloced
        self.bytes_malloced = 0
        curr_heap_size = 0
        freed_size = 0

        # mark objects reachable by objects with a finalizer, but not those
        # themselves. add their size to curr_heap_size, since they always
        # survive the collection
        hdr = self.malloced_objects_with_finalizer
        while hdr:
            next = hdr.next
            typeid = hdr.typeid >> 1
            gc_info = llmemory.cast_ptr_to_adr(hdr)
            obj = gc_info + size_gc_header
            if not hdr.typeid & 1:
                self.add_reachable_to_stack(obj, objects)
            addr = llmemory.cast_ptr_to_adr(hdr)
            size = self.fixed_size(typeid)
            if self.is_varsize(typeid):
                length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
                size += self.varsize_item_sizes(typeid) * length
            estimate = raw_malloc_usage(size_gc_header + size)
            curr_heap_size += estimate
            hdr = next

        # mark thinks on the mark stack and put their descendants onto the
        # stack until the stack is empty
        while objects.non_empty():  #mark
            curr = objects.pop()
            gc_info = curr - size_gc_header
            hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
            if hdr.typeid & 1:
                continue
            self.add_reachable_to_stack(curr, objects)
            hdr.typeid = hdr.typeid | 1
        objects.delete()
        # also mark self.curpool
        if self.curpool:
            gc_info = llmemory.cast_ptr_to_adr(self.curpool) - size_gc_header
            hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
            hdr.typeid = hdr.typeid | 1
        # go through the list of objects containing weak pointers
        # and kill the links if they go to dead objects
        # if the object itself is not marked, free it
        hdr = self.objects_with_weak_pointers
        surviving = lltype.nullptr(self.HDR)
        while hdr:
            typeid = hdr.typeid >> 1
            next = hdr.next
            addr = llmemory.cast_ptr_to_adr(hdr)
            size = self.fixed_size(typeid)
            estimate = raw_malloc_usage(size_gc_header + size)
            if hdr.typeid & 1:
                typeid = hdr.typeid >> 1
                offset = self.weakpointer_offset(typeid)
                hdr.typeid = hdr.typeid & (~1)
                gc_info = llmemory.cast_ptr_to_adr(hdr)
                weakref_obj = gc_info + size_gc_header
                pointing_to = (weakref_obj + offset).address[0]
                if pointing_to:
                    gc_info_pointing_to = pointing_to - size_gc_header
                    hdr_pointing_to = llmemory.cast_adr_to_ptr(
                        gc_info_pointing_to, self.HDRPTR)
                    # pointed to object will die
                    # XXX what to do if the object has a finalizer which resurrects
                    # the object?
                    if not hdr_pointing_to.typeid & 1:
                        (weakref_obj + offset).address[0] = NULL
                hdr.next = surviving
                surviving = hdr
                curr_heap_size += estimate
            else:
                freed_size += estimate
                raw_free(addr)
            hdr = next
        self.objects_with_weak_pointers = surviving
        # sweep: delete objects without del if they are not marked
        # unmark objects without del that are marked
        firstpoolnode = lltype.malloc(self.POOLNODE, flavor='raw')
        firstpoolnode.linkedlist = self.malloced_objects
        firstpoolnode.nextnode = self.poolnodes
        prevpoolnode = lltype.nullptr(self.POOLNODE)
        poolnode = firstpoolnode
        while poolnode:   #sweep
            ppnext = llmemory.cast_ptr_to_adr(poolnode)
            ppnext += llmemory.offsetof(self.POOLNODE, 'linkedlist')
            hdr = poolnode.linkedlist
            while hdr:  #sweep
                typeid = hdr.typeid >> 1
                next = hdr.next
                addr = llmemory.cast_ptr_to_adr(hdr)
                size = self.fixed_size(typeid)
                if self.is_varsize(typeid):
                    length = (addr + size_gc_header + self.varsize_offset_to_length(typeid)).signed[0]
                    size += self.varsize_item_sizes(typeid) * length
                estimate = raw_malloc_usage(size_gc_header + size)
                if hdr.typeid & 1:
                    hdr.typeid = hdr.typeid & (~1)
                    ppnext.address[0] = addr
                    ppnext = llmemory.cast_ptr_to_adr(hdr)
                    ppnext += llmemory.offsetof(self.HDR, 'next')
                    curr_heap_size += estimate
                else:
                    freed_size += estimate
                    raw_free(addr)
                hdr = next
            ppnext.address[0] = llmemory.NULL
            next = poolnode.nextnode
            if not poolnode.linkedlist and prevpoolnode:
                # completely empty node
                prevpoolnode.nextnode = next
                lltype.free(poolnode, flavor='raw')
            else:
                prevpoolnode = poolnode
            poolnode = next
        self.malloced_objects = firstpoolnode.linkedlist
        self.poolnodes = firstpoolnode.nextnode
        lltype.free(firstpoolnode, flavor='raw')
        #llop.debug_view(lltype.Void, self.malloced_objects, self.malloced_objects_with_finalizer, size_gc_header)

        end_time = time.time()
        compute_time = start_time - self.prev_collect_end_time
        collect_time = end_time - start_time

        garbage_collected = old_malloced - (curr_heap_size - self.heap_usage)

        if (collect_time * curr_heap_size >
            0.02 * garbage_collected * compute_time): 
            self.bytes_malloced_threshold += self.bytes_malloced_threshold / 2
        if (collect_time * curr_heap_size <
            0.005 * garbage_collected * compute_time):
            self.bytes_malloced_threshold /= 2

        # Use atleast as much memory as current live objects.
        if curr_heap_size > self.bytes_malloced_threshold:
            self.bytes_malloced_threshold = curr_heap_size

        # Cap at 1/4 GB
        self.bytes_malloced_threshold = min(self.bytes_malloced_threshold,
                                            256 * 1024 * 1024)
        self.total_collection_time += collect_time
        self.prev_collect_end_time = end_time
        if DEBUG_PRINT:
            llop.debug_print(lltype.Void,
                             "  malloced since previous collection:",
                             old_malloced, "bytes")
            llop.debug_print(lltype.Void,
                             "  heap usage at start of collection: ",
                             self.heap_usage + old_malloced, "bytes")
            llop.debug_print(lltype.Void,
                             "  freed:                             ",
                             freed_size, "bytes")
            llop.debug_print(lltype.Void,
                             "  new heap usage:                    ",
                             curr_heap_size, "bytes")
            llop.debug_print(lltype.Void,
                             "  total time spent collecting:       ",
                             self.total_collection_time, "seconds")
            llop.debug_print(lltype.Void,
                             "  collecting time:                   ",
                             collect_time)
            llop.debug_print(lltype.Void,
                             "  computing time:                    ",
                             collect_time)
            llop.debug_print(lltype.Void,
                             "  new threshold:                     ",
                             self.bytes_malloced_threshold)
##        llop.debug_view(lltype.Void, self.malloced_objects, self.poolnodes,
##                        size_gc_header)
        assert self.heap_usage + old_malloced == curr_heap_size + freed_size

        self.heap_usage = curr_heap_size
        hdr = self.malloced_objects_with_finalizer
        self.malloced_objects_with_finalizer = lltype.nullptr(self.HDR)
        last = lltype.nullptr(self.HDR)
        while hdr:
            next = hdr.next
            if hdr.typeid & 1:
                hdr.next = lltype.nullptr(self.HDR)
                if not self.malloced_objects_with_finalizer:
                    self.malloced_objects_with_finalizer = hdr
                else:
                    last.next = hdr
                hdr.typeid = hdr.typeid & (~1)
                last = hdr
            else:
                obj = llmemory.cast_ptr_to_adr(hdr) + size_gc_header
                finalizer = self.getfinalizer(hdr.typeid >> 1)
                # make malloced_objects_with_finalizer consistent
                # for the sake of a possible collection caused by finalizer
                if not self.malloced_objects_with_finalizer:
                    self.malloced_objects_with_finalizer = next
                else:
                    last.next = next
                hdr.next = self.malloced_objects
                self.malloced_objects = hdr
                #llop.debug_view(lltype.Void, self.malloced_objects, self.malloced_objects_with_finalizer, size_gc_header)
                finalizer(obj)
                if not self.collect_in_progress: # another collection was caused?
                    llop.debug_print(lltype.Void, "outer collect interrupted "
                                                  "by recursive collect")
                    return
                if not last:
                    if self.malloced_objects_with_finalizer == next:
                        self.malloced_objects_with_finalizer = lltype.nullptr(self.HDR)
                    else:
                        # now it gets annoying: finalizer caused a malloc of something
                        # with a finalizer
                        last = self.malloced_objects_with_finalizer
                        while last.next != next:
                            last = last.next
                            last.next = lltype.nullptr(self.HDR)
                else:
                    last.next = lltype.nullptr(self.HDR)
            hdr = next
        self.collect_in_progress = False

    STAT_HEAP_USAGE     = 0
    STAT_BYTES_MALLOCED = 1
    STATISTICS_NUMBERS  = 2

    def add_reachable_to_stack(self, obj, objects):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        gc_info = obj - size_gc_header
        hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
        typeid = hdr.typeid >> 1
        offsets = self.offsets_to_gc_pointers(typeid)
        i = 0
        while i < len(offsets):
            pointer = obj + offsets[i]
            objects.append(pointer.address[0])
            i += 1
        if self.is_varsize(typeid):
            offset = self.varsize_offset_to_variable_part(
                typeid)
            length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
            obj += offset
            offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
            itemlength = self.varsize_item_sizes(typeid)
            i = 0
            while i < length:
                item = obj + itemlength * i
                j = 0
                while j < len(offsets):
                    pointer = item + offsets[j]
                    objects.append(pointer.address[0])
                    j += 1
                i += 1

    def statistics(self, index):
        # no memory allocation here!
        if index == self.STAT_HEAP_USAGE:
            return self.heap_usage
        if index == self.STAT_BYTES_MALLOCED:
            return self.bytes_malloced
        return -1

    def init_gc_object(self, addr, typeid):
        hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
        hdr.typeid = typeid << 1

    def init_gc_object_immortal(self, addr, typeid):
        # prebuilt gc structures always have the mark bit set
        hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
        hdr.typeid = (typeid << 1) | 1

    # experimental support for thread cloning
    def x_swap_pool(self, newpool):
        # Set newpool as the current pool (create one if newpool == NULL).
        # All malloc'ed objects are put into the current pool;this is a
        # way to separate objects depending on when they were allocated.
        size_gc_header = self.gcheaderbuilder.size_gc_header
        # invariant: each POOL GcStruct is at the _front_ of a linked list
        # of malloced objects.
        oldpool = self.curpool
        #llop.debug_print(lltype.Void, 'x_swap_pool',
        #                 lltype.cast_ptr_to_int(oldpool),
        #                 lltype.cast_ptr_to_int(newpool))
        if not oldpool:
            # make a fresh pool object, which is automatically inserted at the
            # front of the current list
            oldpool = lltype.malloc(self.POOL)
            addr = llmemory.cast_ptr_to_adr(oldpool)
            addr -= size_gc_header
            hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
            # put this new POOL object in the poolnodes list
            node = lltype.malloc(self.POOLNODE, flavor="raw")
            node.linkedlist = hdr
            node.nextnode = self.poolnodes
            self.poolnodes = node
        else:
            # manually insert oldpool at the front of the current list
            addr = llmemory.cast_ptr_to_adr(oldpool)
            addr -= size_gc_header
            hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
            hdr.next = self.malloced_objects

        newpool = lltype.cast_opaque_ptr(self.POOLPTR, newpool)
        if newpool:
            # newpool is at the front of the new linked list to install
            addr = llmemory.cast_ptr_to_adr(newpool)
            addr -= size_gc_header
            hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
            self.malloced_objects = hdr.next
            # invariant: now that objects in the hdr.next list are accessible
            # through self.malloced_objects, make sure they are not accessible
            # via poolnodes (which has a node pointing to newpool):
            hdr.next = lltype.nullptr(self.HDR)
        else:
            # start a fresh new linked list
            self.malloced_objects = lltype.nullptr(self.HDR)
        self.curpool = newpool
        return lltype.cast_opaque_ptr(X_POOL_PTR, oldpool)

    def x_clone(self, clonedata):
        # Recursively clone the gcobject and everything it points to,
        # directly or indirectly -- but stops at objects that are not
        # in the specified pool.  A new pool is built to contain the
        # copies, and the 'gcobjectptr' and 'pool' fields of clonedata
        # are adjusted to refer to the result.
        CURPOOL_FLAG = sys.maxint // 2 + 1

        # install a new pool into which all the mallocs go
        curpool = self.x_swap_pool(lltype.nullptr(X_POOL))

        size_gc_header = self.gcheaderbuilder.size_gc_header
        oldobjects = self.AddressLinkedList()
        # if no pool specified, use the current pool as the 'source' pool
        oldpool = clonedata.pool or curpool
        oldpool = lltype.cast_opaque_ptr(self.POOLPTR, oldpool)
        addr = llmemory.cast_ptr_to_adr(oldpool)
        addr -= size_gc_header

        hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
        hdr = hdr.next   # skip the POOL object itself
        while hdr:
            next = hdr.next
            hdr.typeid |= CURPOOL_FLAG   # mark all objects from malloced_list
            hdr.next = lltype.nullptr(self.HDR)  # abused to point to the copy
            oldobjects.append(llmemory.cast_ptr_to_adr(hdr))
            hdr = next

        # a stack of addresses of places that still points to old objects
        # and that must possibly be fixed to point to a new copy
        stack = self.AddressLinkedList()
        stack.append(llmemory.cast_ptr_to_adr(clonedata)
                     + llmemory.offsetof(X_CLONE, 'gcobjectptr'))
        while stack.non_empty():
            gcptr_addr = stack.pop()
            oldobj_addr = gcptr_addr.address[0]
            if not oldobj_addr:
                continue   # pointer is NULL
            oldhdr = llmemory.cast_adr_to_ptr(oldobj_addr - size_gc_header,
                                              self.HDRPTR)
            typeid = oldhdr.typeid
            if not (typeid & CURPOOL_FLAG):
                continue   # ignore objects that were not in the malloced_list
            newhdr = oldhdr.next      # abused to point to the copy
            if not newhdr:
                typeid = (typeid & ~CURPOOL_FLAG) >> 1
                size = self.fixed_size(typeid)
                # XXX! collect() at the beginning if the free heap is low
                if self.is_varsize(typeid):
                    itemsize = self.varsize_item_sizes(typeid)
                    offset_to_length = self.varsize_offset_to_length(typeid)
                    length = (oldobj_addr + offset_to_length).signed[0]
                    newobj = self.malloc_varsize(typeid, length, size,
                                                 itemsize, offset_to_length,
                                                 False)
                    size += length*itemsize
                else:
                    newobj = self.malloc_fixedsize(typeid, size, False)
                    length = -1

                newobj_addr = llmemory.cast_ptr_to_adr(newobj)

                #llop.debug_print(lltype.Void, 'clone',
                #                 llmemory.cast_adr_to_int(oldobj_addr),
                #                 '->', llmemory.cast_adr_to_int(newobj_addr),
                #                 'typeid', typeid,
                #                 'length', length)

                newhdr_addr = newobj_addr - size_gc_header
                newhdr = llmemory.cast_adr_to_ptr(newhdr_addr, self.HDRPTR)

                saved_id   = newhdr.typeid    # XXX hack needed for genc
                saved_next = newhdr.next      # where size_gc_header == 0
                raw_memcopy(oldobj_addr, newobj_addr, size)
                newhdr.typeid = saved_id
                newhdr.next   = saved_next

                offsets = self.offsets_to_gc_pointers(typeid)
                i = 0
                while i < len(offsets):
                    pointer_addr = newobj_addr + offsets[i]
                    stack.append(pointer_addr)
                    i += 1

                if length > 0:
                    offsets = self.varsize_offsets_to_gcpointers_in_var_part(
                        typeid)
                    itemlength = self.varsize_item_sizes(typeid)
                    offset = self.varsize_offset_to_variable_part(typeid)
                    itembaseaddr = newobj_addr + offset
                    i = 0
                    while i < length:
                        item = itembaseaddr + itemlength * i
                        j = 0
                        while j < len(offsets):
                            pointer_addr = item + offsets[j]
                            stack.append(pointer_addr)
                            j += 1
                        i += 1

                oldhdr.next = newhdr
            newobj_addr = llmemory.cast_ptr_to_adr(newhdr) + size_gc_header
            gcptr_addr.address[0] = newobj_addr
        stack.delete()

        # re-create the original linked list
        next = lltype.nullptr(self.HDR)
        while oldobjects.non_empty():
            hdr = llmemory.cast_adr_to_ptr(oldobjects.pop(), self.HDRPTR)
            hdr.typeid &= ~CURPOOL_FLAG   # reset the flag
            hdr.next = next
            next = hdr
        oldobjects.delete()

        # consistency check
        addr = llmemory.cast_ptr_to_adr(oldpool)
        addr -= size_gc_header
        hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
        assert hdr.next == next

        # build the new pool object collecting the new objects, and
        # reinstall the pool that was current at the beginning of x_clone()
        clonedata.pool = self.x_swap_pool(curpool)

    def add_reachable_to_stack2(self, obj, objects, target_addr, source_addr):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        gc_info = obj - size_gc_header
        hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
        if hdr.typeid & 1:
            return
        typeid = hdr.typeid >> 1
        offsets = self.offsets_to_gc_pointers(typeid)
        i = 0
        while i < len(offsets):
            pointer = obj + offsets[i]
            # -------------------------------------------------
            # begin difference from collect
            if pointer.address[0] == target_addr:
                pointer.address[0] = source_addr
            # end difference from collect
            # -------------------------------------------------
            objects.append(pointer.address[0])
            i += 1
        if self.is_varsize(typeid):
            offset = self.varsize_offset_to_variable_part(
                typeid)
            length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
            obj += offset
            offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
            itemlength = self.varsize_item_sizes(typeid)
            i = 0
            while i < length:
                item = obj + itemlength * i
                j = 0
                while j < len(offsets):
                    pointer = item + offsets[j]
                    # -------------------------------------------------
                    # begin difference from collect
                    if pointer.address[0] == target_addr:
                        pointer.address[0] = source_addr
                    ## end difference from collect
                    # -------------------------------------------------
                    objects.append(pointer.address[0])
                    j += 1
                i += 1


    def x_become(self, target_addr, source_addr):
        # 1. mark from the roots, and also the objects that objects-with-del
        #    point to (using the list of malloced_objects_with_finalizer)
        # 2. walk the list of objects-without-del and free the ones not marked
        # 3. walk the list of objects-with-del and for the ones not marked:
        #    call __del__, move the object to the list of object-without-del
        import time
        from pypy.rpython.lltypesystem.lloperation import llop
        if DEBUG_PRINT:
            llop.debug_print(lltype.Void, 'collecting...')
        start_time = time.time()
        roots = self.get_roots()
        size_gc_header = self.gcheaderbuilder.size_gc_header
##        llop.debug_view(lltype.Void, self.malloced_objects, self.poolnodes,
##                        size_gc_header)

        # push the roots on the mark stack
        objects = self.AddressLinkedList() # mark stack
        while 1:
            curr = roots.pop()
            if curr == NULL:
                break
            # roots is a list of addresses to addresses:
            objects.append(curr.address[0])
            # the last sweep did not clear the mark bit of static roots, 
            # since they are not in the malloced_objects list
            gc_info = curr.address[0] - size_gc_header
            hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
            hdr.typeid = hdr.typeid & (~1)
        free_non_gc_object(roots)
        # from this point onwards, no more mallocs should be possible
        old_malloced = self.bytes_malloced
        self.bytes_malloced = 0
        curr_heap_size = 0
        freed_size = 0

        # mark objects reachable by objects with a finalizer, but not those
        # themselves. add their size to curr_heap_size, since they always
        # survive the collection
        hdr = self.malloced_objects_with_finalizer
        while hdr:
            next = hdr.next
            typeid = hdr.typeid >> 1
            gc_info = llmemory.cast_ptr_to_adr(hdr)
            obj = gc_info + size_gc_header
            self.add_reachable_to_stack2(obj, objects, target_addr, source_addr)
            addr = llmemory.cast_ptr_to_adr(hdr)
            size = self.fixed_size(typeid)
            if self.is_varsize(typeid):
                length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
                size += self.varsize_item_sizes(typeid) * length
            estimate = raw_malloc_usage(size_gc_header + size)
            curr_heap_size += estimate
            hdr = next

        # mark thinks on the mark stack and put their descendants onto the
        # stack until the stack is empty
        while objects.non_empty():  #mark
            curr = objects.pop()
            self.add_reachable_to_stack2(curr, objects, target_addr, source_addr)
            gc_info = curr - size_gc_header
            hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
            if hdr.typeid & 1:
                continue
            hdr.typeid = hdr.typeid | 1
        objects.delete()
        # also mark self.curpool
        if self.curpool:
            gc_info = llmemory.cast_ptr_to_adr(self.curpool) - size_gc_header
            hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
            hdr.typeid = hdr.typeid | 1

        # sweep: delete objects without del if they are not marked
        # unmark objects without del that are marked
        firstpoolnode = lltype.malloc(self.POOLNODE, flavor='raw')
        firstpoolnode.linkedlist = self.malloced_objects
        firstpoolnode.nextnode = self.poolnodes
        prevpoolnode = lltype.nullptr(self.POOLNODE)
        poolnode = firstpoolnode
        while poolnode:   #sweep
            ppnext = llmemory.cast_ptr_to_adr(poolnode)
            ppnext += llmemory.offsetof(self.POOLNODE, 'linkedlist')
            hdr = poolnode.linkedlist
            while hdr:  #sweep
                typeid = hdr.typeid >> 1
                next = hdr.next
                addr = llmemory.cast_ptr_to_adr(hdr)
                size = self.fixed_size(typeid)
                if self.is_varsize(typeid):
                    length = (addr + size_gc_header + self.varsize_offset_to_length(typeid)).signed[0]
                    size += self.varsize_item_sizes(typeid) * length
                estimate = raw_malloc_usage(size_gc_header + size)
                if hdr.typeid & 1:
                    hdr.typeid = hdr.typeid & (~1)
                    ppnext.address[0] = addr
                    ppnext = llmemory.cast_ptr_to_adr(hdr)
                    ppnext += llmemory.offsetof(self.HDR, 'next')
                    curr_heap_size += estimate
                else:
                    freed_size += estimate
                    raw_free(addr)
                hdr = next
            ppnext.address[0] = llmemory.NULL
            next = poolnode.nextnode
            if not poolnode.linkedlist and prevpoolnode:
                # completely empty node
                prevpoolnode.nextnode = next
                lltype.free(poolnode, flavor='raw')
            else:
                prevpoolnode = poolnode
            poolnode = next
        self.malloced_objects = firstpoolnode.linkedlist
        self.poolnodes = firstpoolnode.nextnode
        lltype.free(firstpoolnode, flavor='raw')

        if curr_heap_size > self.bytes_malloced_threshold:
            self.bytes_malloced_threshold = curr_heap_size
        end_time = time.time()
        self.total_collection_time += end_time - start_time
        if DEBUG_PRINT:
            llop.debug_print(lltype.Void,
                             "  malloced since previous collection:",
                             old_malloced, "bytes")
            llop.debug_print(lltype.Void,
                             "  heap usage at start of collection: ",
                             self.heap_usage + old_malloced, "bytes")
            llop.debug_print(lltype.Void,
                             "  freed:                             ",
                             freed_size, "bytes")
            llop.debug_print(lltype.Void,
                             "  new heap usage:                    ",
                             curr_heap_size, "bytes")
            llop.debug_print(lltype.Void,
                             "  total time spent collecting:       ",
                             self.total_collection_time, "seconds")
##        llop.debug_view(lltype.Void, self.malloced_objects, self.poolnodes,
##                        size_gc_header)
        assert self.heap_usage + old_malloced == curr_heap_size + freed_size

        # call finalizers if needed
        self.heap_usage = curr_heap_size
        hdr = self.malloced_objects_with_finalizer
        self.malloced_objects_with_finalizer = lltype.nullptr(self.HDR)
        while hdr:
            next = hdr.next
            if hdr.typeid & 1:
                hdr.next = self.malloced_objects_with_finalizer
                self.malloced_objects_with_finalizer = hdr
                hdr.typeid = hdr.typeid & (~1)
            else:
                obj = llmemory.cast_ptr_to_adr(hdr) + size_gc_header
                finalizer = self.getfinalizer(hdr.typeid >> 1)
                finalizer(obj)
                hdr.next = self.malloced_objects
                self.malloced_objects = hdr
            hdr = next

class SemiSpaceGC(GCBase):
    _alloc_flavor_ = "raw"
    moving_gc = True

    HDR = lltype.Struct('header', ('forw', llmemory.Address),
                                  ('typeid', lltype.Signed))

    def __init__(self, AddressLinkedList, space_size=4096,
                 max_space_size=sys.maxint//2+1,
                 get_roots=None):
        self.space_size = space_size
        self.max_space_size = max_space_size
        self.get_roots = get_roots
        self.gcheaderbuilder = GCHeaderBuilder(self.HDR)
        self.AddressLinkedList = AddressLinkedList

    def setup(self):
        self.tospace = llarena.arena_malloc(self.space_size, True)
        debug_assert(bool(self.tospace), "couldn't allocate tospace")
        self.top_of_space = self.tospace + self.space_size
        self.fromspace = llarena.arena_malloc(self.space_size, True)
        debug_assert(bool(self.fromspace), "couldn't allocate fromspace")
        self.free = self.tospace
        self.objects_with_finalizers = self.AddressLinkedList()
        self.run_finalizers = self.AddressLinkedList()
        self.executing_finalizers = False
        self.objects_with_weakrefs = self.AddressLinkedList()

    def malloc_fixedsize(self, typeid, size, can_collect, has_finalizer=False,
                         contains_weakptr=False):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        if raw_malloc_usage(totalsize) > self.top_of_space - self.free:
            if not can_collect or not self.obtain_free_space(totalsize):
                raise memoryError
        result = self.free
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid)
        self.free += totalsize
        if has_finalizer:
            self.objects_with_finalizers.append(result + size_gc_header)
        if contains_weakptr:
            self.objects_with_weakrefs.append(result + size_gc_header)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    def malloc_varsize(self, typeid, length, size, itemsize, offset_to_length,
                       can_collect, has_finalizer=False):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size
        try:
            varsize = ovfcheck(itemsize * length)
            totalsize = ovfcheck(nonvarsize + varsize)
        except OverflowError:
            raise memoryError
        if raw_malloc_usage(totalsize) > self.top_of_space - self.free:
            if not can_collect or not self.obtain_free_space(totalsize):
                raise memoryError
        result = self.free
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid)
        (result + size_gc_header + offset_to_length).signed[0] = length
        self.free += llarena.round_up_for_allocation(totalsize)
        if has_finalizer:
            self.objects_with_finalizers.append(result + size_gc_header)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    # for now, the spaces are filled with zeroes in advance
    malloc_fixedsize_clear = malloc_fixedsize
    malloc_varsize_clear   = malloc_varsize

    def obtain_free_space(self, needed):
        # XXX for bonus points do big objects differently
        needed = raw_malloc_usage(needed)
        self.semispace_collect()
        missing = needed - (self.top_of_space - self.free)
        if missing <= 0:
            return True      # success
        else:
            # first check if the object could possibly fit
            proposed_size = self.space_size
            while missing > 0:
                if proposed_size >= self.max_space_size:
                    return False    # no way
                missing -= proposed_size
                proposed_size *= 2
            # For address space fragmentation reasons, we double the space
            # size possibly several times, moving the objects at each step,
            # instead of going directly for the final size.  We assume that
            # it's a rare case anyway.
            while self.space_size < proposed_size:
                if not self.double_space_size():
                    return False
            debug_assert(needed <= self.top_of_space - self.free,
                         "double_space_size() failed to do its job")
            return True

    def double_space_size(self):
        old_fromspace = self.fromspace
        newsize = self.space_size * 2
        newspace = llarena.arena_malloc(newsize, True)
        if not newspace:
            return False    # out of memory
        llarena.arena_free(old_fromspace)
        self.fromspace = newspace
        # now self.tospace contains the existing objects and
        # self.fromspace is the freshly allocated bigger space

        self.semispace_collect(size_changing=True)
        self.top_of_space = self.tospace + newsize
        # now self.tospace is the freshly allocated bigger space,
        # and self.fromspace is the old smaller space, now empty
        llarena.arena_free(self.fromspace)

        newspace = llarena.arena_malloc(newsize, True)
        if not newspace:
            # Complex failure case: we have in self.tospace a big chunk
            # of memory, and the two smaller original spaces are already gone.
            # Unsure if it's worth these efforts, but we can artificially
            # split self.tospace in two again...
            self.max_space_size = self.space_size    # don't try to grow again,
            #              because doing arena_free(self.fromspace) would crash
            self.fromspace = self.tospace + self.space_size
            self.top_of_space = self.fromspace
            debug_assert(self.free <= self.top_of_space,
                         "unexpected growth of GC space usage during collect")
            return False     # out of memory

        self.fromspace = newspace
        self.space_size = newsize
        return True    # success

    def collect(self):
        self.semispace_collect()
        # the indirection is required by the fact that collect() is referred
        # to by the gc transformer, and the default argument would crash

    def semispace_collect(self, size_changing=False):
        #llop.debug_print(lltype.Void, 'semispace_collect', int(size_changing))
        tospace = self.fromspace
        fromspace = self.tospace
        self.fromspace = fromspace
        self.tospace = tospace
        self.top_of_space = tospace + self.space_size
        scan = self.free = tospace
        self.collect_roots()
        scan = self.scan_copied(scan)
        if self.objects_with_weakrefs.non_empty():
            self.invalidate_weakrefs()
        if self.run_finalizers.non_empty():
            self.update_run_finalizers()
        if self.objects_with_finalizers.non_empty():
            self.deal_with_objects_with_finalizers()
        scan = self.scan_copied(scan)
        if not size_changing:
            llarena.arena_reset(fromspace, self.space_size, True)
            self.execute_finalizers()

    def scan_copied(self, scan):
        while scan < self.free:
            curr = scan + self.size_gc_header()
            self.trace_and_copy(curr)
            scan += self.size_gc_header() + self.get_size(curr)
        return scan

    def collect_roots(self):
        roots = self.get_roots()
        while 1:
            root = roots.pop()
            if root == NULL:
                break
            root.address[0] = self.copy(root.address[0])
        free_non_gc_object(roots)

    def copy(self, obj):
        # Objects not living the GC heap have all been initialized by
        # setting their 'forw' address so that it points to themselves.
        # The logic below will thus simply return 'obj' if 'obj' is prebuilt.
##         print "copying regularly", obj,
        if self.is_forwarded(obj):
##             print "already copied to", self.get_forwarding_address(obj)
            return self.get_forwarding_address(obj)
        else:
            newaddr = self.free
            totalsize = self.size_gc_header() + self.get_size(obj)
            llarena.arena_reserve(newaddr, totalsize)
            raw_memcopy(obj - self.size_gc_header(), newaddr, totalsize)
            self.free += totalsize
            newobj = newaddr + self.size_gc_header()
##             print "to", newobj
            self.set_forwarding_address(obj, newobj)
            return newobj

    def trace_and_copy(self, obj):
        gc_info = self.header(obj)
        typeid = gc_info.typeid
        offsets = self.offsets_to_gc_pointers(typeid)
        i = 0
        while i < len(offsets):
            pointer = obj + offsets[i]
            if pointer.address[0] != NULL:
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
                    if pointer.address[0] != NULL:
                        pointer.address[0] = self.copy(pointer.address[0])
                    j += 1
                i += 1

    def is_forwarded(self, obj):
        return self.header(obj).forw != NULL

    def get_forwarding_address(self, obj):
        return self.header(obj).forw

    def set_forwarding_address(self, obj, newobj):
        gc_info = self.header(obj)
        gc_info.forw = newobj

    def get_size(self, obj):
        typeid = self.header(obj).typeid
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            lenaddr = obj + self.varsize_offset_to_length(typeid)
            length = lenaddr.signed[0]
            size += length * self.varsize_item_sizes(typeid)
            size = llarena.round_up_for_allocation(size)
        return size

    def header(self, addr):
        addr -= self.gcheaderbuilder.size_gc_header
        return llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))

    def init_gc_object(self, addr, typeid):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        #hdr.forw = NULL   -- unneeded, the space is initially filled with zero
        hdr.typeid = typeid

    def init_gc_object_immortal(self, addr, typeid):
        # immortal objects always have forward to themselves
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.forw = addr + self.gcheaderbuilder.size_gc_header
        hdr.typeid = typeid

    def deal_with_objects_with_finalizers(self):
        # walk over list of objects with finalizers
        # if it is not copied, add it to the list of to-be-called finalizers
        # and copy it, to me make the finalizer runnable
        new_with_finalizer = self.AddressLinkedList()
        while self.objects_with_finalizers.non_empty():
            obj = self.objects_with_finalizers.pop()
            if self.is_forwarded(obj):
                new_with_finalizer.append(self.get_forwarding_address(obj))
            else:
                self.run_finalizers.append(self.copy(obj))
        self.objects_with_finalizers.delete()
        self.objects_with_finalizers = new_with_finalizer

    def invalidate_weakrefs(self):
        # walk over list of objects that contain weakrefs
        # if the object it references survives then update the weakref
        # otherwise invalidate the weakref
        new_with_weakref = self.AddressLinkedList()
        while self.objects_with_weakrefs.non_empty():
            obj = self.objects_with_weakrefs.pop()
            if not self.is_forwarded(obj):
                continue # weakref itself dies
            obj = self.get_forwarding_address(obj)
            offset = self.weakpointer_offset(self.header(obj).typeid)
            pointing_to = (obj + offset).address[0]
            if pointing_to:
                if self.is_forwarded(pointing_to):
                    (obj + offset).address[0] = self.get_forwarding_address(
                        pointing_to)
                    new_with_weakref.append(obj)
                else:
                    (obj + offset).address[0] = NULL
        self.objects_with_weakrefs.delete()
        self.objects_with_weakrefs = new_with_weakref

    def update_run_finalizers(self):
        # we are in an inner collection, caused by a finalizer
        # the run_finalizers objects need to be copied
        new_run_finalizer = self.AddressLinkedList()
        while self.run_finalizers.non_empty():
            obj = self.run_finalizers.pop()
            new_run_finalizer.append(self.copy(obj))
        self.run_finalizers.delete()
        self.run_finalizers = new_run_finalizer

    def execute_finalizers(self):
        if self.executing_finalizers:
            return    # the outer invocation of execute_finalizers() will do it
        self.executing_finalizers = True
        try:
            while self.run_finalizers.non_empty():
                obj = self.run_finalizers.pop()
                hdr = self.header(obj)
                finalizer = self.getfinalizer(hdr.typeid)
                finalizer(obj)
        finally:
            self.executing_finalizers = False

    STATISTICS_NUMBERS = 0


# ____________________________________________________________

def choose_gc_from_config(config):
    """Return a (GCClass, GC_PARAMS) from the given config object.
    """
    config.translation.gc = "framework"
    if config.translation.frameworkgc == "marksweep":
        GC_PARAMS = {'start_heap_size': 8*1024*1024} # XXX adjust
        return MarkSweepGC, GC_PARAMS
    elif config.translation.frameworkgc == "semispace":
        GC_PARAMS = {'space_size': 8*1024*1024} # XXX adjust
        return SemiSpaceGC, GC_PARAMS
    else:
        raise ValueError("unknown value for frameworkgc: %r" % (
            config.translation.frameworkgc,))
