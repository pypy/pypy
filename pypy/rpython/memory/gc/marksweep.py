from pypy.rpython.lltypesystem.llmemory import raw_malloc, raw_free
from pypy.rpython.lltypesystem.llmemory import raw_memcopy, raw_memclear
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rpython.memory.support import get_address_stack
from pypy.rpython.memory.gcheader import GCHeaderBuilder
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, llgroup
from pypy.rlib.objectmodel import free_non_gc_object
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rlib.debug import debug_print, debug_start, debug_stop
from pypy.rpython.memory.gc.base import GCBase


import sys, os

X_POOL = lltype.GcOpaqueType('gc.pool')
X_POOL_PTR = lltype.Ptr(X_POOL)
X_CLONE = lltype.GcStruct('CloneData', ('gcobjectptr', llmemory.GCREF),
                                       ('pool',        X_POOL_PTR))
X_CLONE_PTR = lltype.Ptr(X_CLONE)

FL_WITHHASH = 0x01
FL_CURPOOL  = 0x02

memoryError = MemoryError()
class MarkSweepGC(GCBase):
    HDR = lltype.ForwardReference()
    HDRPTR = lltype.Ptr(HDR)
    # need to maintain a linked list of malloced objects, since we used the
    # systems allocator and can't walk the heap
    HDR.become(lltype.Struct('header', ('typeid16', llgroup.HALFWORD),
                                       ('mark', lltype.Bool),
                                       ('flags', lltype.Char),
                                       ('next', HDRPTR)))
    typeid_is_in_field = 'typeid16'
    withhash_flag_is_in_field = 'flags', FL_WITHHASH

    POOL = lltype.GcStruct('gc_pool')
    POOLPTR = lltype.Ptr(POOL)

    POOLNODE = lltype.ForwardReference()
    POOLNODEPTR = lltype.Ptr(POOLNODE)
    POOLNODE.become(lltype.Struct('gc_pool_node', ('linkedlist', HDRPTR),
                                                  ('nextnode', POOLNODEPTR)))

    # the following values override the default arguments of __init__ when
    # translating to a real backend.
    TRANSLATION_PARAMS = {'start_heap_size': 8*1024*1024} # XXX adjust

    def __init__(self, config, start_heap_size=4096, **kwds):
        self.param_start_heap_size = start_heap_size
        GCBase.__init__(self, config, **kwds)

    def setup(self):
        GCBase.setup(self)
        self.heap_usage = 0          # at the end of the latest collection
        self.bytes_malloced = 0      # since the latest collection
        self.bytes_malloced_threshold = self.param_start_heap_size
        self.total_collection_time = 0.0
        self.malloced_objects = lltype.nullptr(self.HDR)
        self.malloced_objects_with_finalizer = lltype.nullptr(self.HDR)
        # these are usually only the small bits of memory that make a
        # weakref object
        self.objects_with_weak_pointers = lltype.nullptr(self.HDR)
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

    def maybe_collect(self):
        if self.bytes_malloced > self.bytes_malloced_threshold:
            self.collect()

    def write_malloc_statistics(self, typeid16, size, result, varsize):
        pass

    def write_free_statistics(self, typeid16, result):
        pass

    def malloc_fixedsize(self, typeid16, size, can_collect,
                         has_finalizer=False, contains_weakptr=False):
        if can_collect:
            self.maybe_collect()
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
        hdr.typeid16 = typeid16
        hdr.mark = False
        hdr.flags = '\x00'
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
        #llop.debug_print(lltype.Void, 'malloc typeid', typeid16,
        #                 '->', llmemory.cast_adr_to_int(result))
        self.write_malloc_statistics(typeid16, tot_size, result, False)
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)
    malloc_fixedsize._dont_inline_ = True

    def malloc_fixedsize_clear(self, typeid16, size, can_collect,
                               has_finalizer=False, contains_weakptr=False):
        if can_collect:
            self.maybe_collect()
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
        hdr.typeid16 = typeid16
        hdr.mark = False
        hdr.flags = '\x00'
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
        #llop.debug_print(lltype.Void, 'malloc typeid', typeid16,
        #                 '->', llmemory.cast_adr_to_int(result))
        self.write_malloc_statistics(typeid16, tot_size, result, False)
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)
    malloc_fixedsize_clear._dont_inline_ = True

    def malloc_varsize(self, typeid16, length, size, itemsize,
                       offset_to_length, can_collect):
        if can_collect:
            self.maybe_collect()
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
        hdr.typeid16 = typeid16
        hdr.mark = False
        hdr.flags = '\x00'
        hdr.next = self.malloced_objects
        self.malloced_objects = hdr
        self.bytes_malloced = bytes_malloced
            
        result += size_gc_header
        #llop.debug_print(lltype.Void, 'malloc_varsize length', length,
        #                 'typeid', typeid16,
        #                 '->', llmemory.cast_adr_to_int(result))
        self.write_malloc_statistics(typeid16, tot_size, result, True)
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)
    malloc_varsize._dont_inline_ = True

    def malloc_varsize_clear(self, typeid16, length, size, itemsize,
                             offset_to_length, can_collect):
        if can_collect:
            self.maybe_collect()
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
        hdr.typeid16 = typeid16
        hdr.mark = False
        hdr.flags = '\x00'
        hdr.next = self.malloced_objects
        self.malloced_objects = hdr
        self.bytes_malloced = bytes_malloced
            
        result += size_gc_header
        #llop.debug_print(lltype.Void, 'malloc_varsize length', length,
        #                 'typeid', typeid16,
        #                 '->', llmemory.cast_adr_to_int(result))
        self.write_malloc_statistics(typeid16, tot_size, result, True)
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)
    malloc_varsize_clear._dont_inline_ = True

    def collect(self, gen=0):
        # 1. mark from the roots, and also the objects that objects-with-del
        #    point to (using the list of malloced_objects_with_finalizer)
        # 2. walk the list of objects-without-del and free the ones not marked
        # 3. walk the list of objects-with-del and for the ones not marked:
        #    call __del__, move the object to the list of object-without-del
        import time
        debug_start("gc-collect")
        start_time = time.time()
        self.collect_in_progress = True
        size_gc_header = self.gcheaderbuilder.size_gc_header
##        llop.debug_view(lltype.Void, self.malloced_objects, self.poolnodes,
##                        size_gc_header)

        # push the roots on the mark stack
        objects = self.AddressStack() # mark stack
        self._mark_stack = objects
        self.root_walker.walk_roots(
            MarkSweepGC._mark_root,  # stack roots
            MarkSweepGC._mark_root,  # static in prebuilt non-gc structures
            MarkSweepGC._mark_root)  # static in prebuilt gc objects

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
            typeid = hdr.typeid16
            gc_info = llmemory.cast_ptr_to_adr(hdr)
            obj = gc_info + size_gc_header
            if not hdr.mark:
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
            if hdr.mark:
                continue
            self.add_reachable_to_stack(curr, objects)
            hdr.mark = True
        objects.delete()
        # also mark self.curpool
        if self.curpool:
            gc_info = llmemory.cast_ptr_to_adr(self.curpool) - size_gc_header
            hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
            hdr.mark = True
        # go through the list of objects containing weak pointers
        # and kill the links if they go to dead objects
        # if the object itself is not marked, free it
        hdr = self.objects_with_weak_pointers
        surviving = lltype.nullptr(self.HDR)
        while hdr:
            typeid = hdr.typeid16
            next = hdr.next
            addr = llmemory.cast_ptr_to_adr(hdr)
            size = self.fixed_size(typeid)
            estimate = raw_malloc_usage(size_gc_header + size)
            if hdr.mark:
                offset = self.weakpointer_offset(typeid)
                hdr.mark = False
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
                    if not hdr_pointing_to.mark:
                        (weakref_obj + offset).address[0] = NULL
                hdr.next = surviving
                surviving = hdr
                curr_heap_size += estimate
            else:
                gc_info = llmemory.cast_ptr_to_adr(hdr)
                weakref_obj = gc_info + size_gc_header
                self.write_free_statistics(typeid, weakref_obj)
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
                typeid = hdr.typeid16
                next = hdr.next
                addr = llmemory.cast_ptr_to_adr(hdr)
                size = self.fixed_size(typeid)
                if self.is_varsize(typeid):
                    length = (addr + size_gc_header + self.varsize_offset_to_length(typeid)).signed[0]
                    size += self.varsize_item_sizes(typeid) * length
                estimate = raw_malloc_usage(size_gc_header + size)
                if hdr.mark:
                    hdr.mark = False
                    ppnext.address[0] = addr
                    ppnext = llmemory.cast_ptr_to_adr(hdr)
                    ppnext += llmemory.offsetof(self.HDR, 'next')
                    curr_heap_size += estimate
                else:
                    gc_info = llmemory.cast_ptr_to_adr(hdr)
                    obj = gc_info + size_gc_header
                    self.write_free_statistics(typeid, obj)
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
        debug_print("  malloced since previous collection:",
                    old_malloced, "bytes")
        debug_print("  heap usage at start of collection: ",
                    self.heap_usage + old_malloced, "bytes")
        debug_print("  freed:                             ",
                    freed_size, "bytes")
        debug_print("  new heap usage:                    ",
                    curr_heap_size, "bytes")
        debug_print("  total time spent collecting:       ",
                    self.total_collection_time, "seconds")
        debug_print("  collecting time:                   ",
                    collect_time)
        debug_print("  computing time:                    ",
                    collect_time)
        debug_print("  new threshold:                     ",
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
            if hdr.mark:
                hdr.next = lltype.nullptr(self.HDR)
                if not self.malloced_objects_with_finalizer:
                    self.malloced_objects_with_finalizer = hdr
                else:
                    last.next = hdr
                hdr.mark = False
                last = hdr
            else:
                obj = llmemory.cast_ptr_to_adr(hdr) + size_gc_header
                finalizer = self.getfinalizer(hdr.typeid16)
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
                    debug_print("outer collect interrupted "
                                "by recursive collect")
                    debug_stop("gc-collect")
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
        debug_stop("gc-collect")

    def _mark_root(self, root):   # 'root' is the address of the GCPTR
        gcobjectaddr = root.address[0]
        self._mark_stack.append(gcobjectaddr)

    def _mark_root_and_clear_bit(self, root):
        gcobjectaddr = root.address[0]
        self._mark_stack.append(gcobjectaddr)
        size_gc_header = self.gcheaderbuilder.size_gc_header
        gc_info = gcobjectaddr - size_gc_header
        hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
        hdr.mark = False

    STAT_HEAP_USAGE     = 0
    STAT_BYTES_MALLOCED = 1
    STATISTICS_NUMBERS  = 2

    def get_type_id(self, obj):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        gc_info = obj - size_gc_header
        hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
        return hdr.typeid16

    def add_reachable_to_stack(self, obj, objects):
        self.trace(obj, self._add_reachable, objects)

    def _add_reachable(pointer, objects):
        obj = pointer.address[0]
        objects.append(obj)
    _add_reachable = staticmethod(_add_reachable)

    def statistics(self, index):
        # no memory allocation here!
        if index == self.STAT_HEAP_USAGE:
            return self.heap_usage
        if index == self.STAT_BYTES_MALLOCED:
            return self.bytes_malloced
        return -1

    def init_gc_object(self, addr, typeid):
        hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
        hdr.typeid16 = typeid
        hdr.mark = False
        hdr.flags = '\x00'

    def init_gc_object_immortal(self, addr, typeid, flags=0):
        # prebuilt gc structures always have the mark bit set
        # ignore flags
        hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
        hdr.typeid16 = typeid
        hdr.mark = True
        hdr.flags = '\x00'

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

        # install a new pool into which all the mallocs go
        curpool = self.x_swap_pool(lltype.nullptr(X_POOL))

        size_gc_header = self.gcheaderbuilder.size_gc_header
        oldobjects = self.AddressStack()
        # if no pool specified, use the current pool as the 'source' pool
        oldpool = clonedata.pool or curpool
        oldpool = lltype.cast_opaque_ptr(self.POOLPTR, oldpool)
        addr = llmemory.cast_ptr_to_adr(oldpool)
        addr -= size_gc_header

        hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
        hdr = hdr.next   # skip the POOL object itself
        while hdr:
            next = hdr.next
            # mark all objects from malloced_list
            hdr.flags = chr(ord(hdr.flags) | FL_CURPOOL)
            hdr.next = lltype.nullptr(self.HDR)  # abused to point to the copy
            oldobjects.append(llmemory.cast_ptr_to_adr(hdr))
            hdr = next

        # a stack of addresses of places that still points to old objects
        # and that must possibly be fixed to point to a new copy
        stack = self.AddressStack()
        stack.append(llmemory.cast_ptr_to_adr(clonedata)
                     + llmemory.offsetof(X_CLONE, 'gcobjectptr'))
        while stack.non_empty():
            gcptr_addr = stack.pop()
            oldobj_addr = gcptr_addr.address[0]
            if not oldobj_addr:
                continue   # pointer is NULL
            oldhdr = llmemory.cast_adr_to_ptr(oldobj_addr - size_gc_header,
                                              self.HDRPTR)
            if not (ord(oldhdr.flags) & FL_CURPOOL):
                continue   # ignore objects that were not in the malloced_list
            newhdr = oldhdr.next      # abused to point to the copy
            if not newhdr:
                typeid = oldhdr.typeid16
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

                saved_id   = newhdr.typeid16  # XXX hack needed for genc
                saved_flg1 = newhdr.mark
                saved_flg2 = newhdr.flags
                saved_next = newhdr.next      # where size_gc_header == 0
                raw_memcopy(oldobj_addr, newobj_addr, size)
                newhdr.typeid16 = saved_id
                newhdr.mark     = saved_flg1
                newhdr.flags    = saved_flg2
                newhdr.next     = saved_next

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
            hdr.flags = chr(ord(hdr.flags) &~ FL_CURPOOL)  # reset the flag
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

    def identityhash(self, obj):
        obj = llmemory.cast_ptr_to_adr(obj)
        hdr = self.header(obj)
        if ord(hdr.flags) & FL_WITHHASH:
            obj += self.get_size(obj)
            return obj.signed[0]
        else:
            return llmemory.cast_adr_to_int(obj)


class PrintingMarkSweepGC(MarkSweepGC):
    _alloc_flavor_ = "raw"
    COLLECT_EVERY = 2000

    def __init__(self, config, **kwds):
        MarkSweepGC.__init__(self, config, **kwds)
        self.count_mallocs = 0

    def maybe_collect(self):
        self.count_mallocs += 1
        if self.count_mallocs > self.COLLECT_EVERY:
            self.collect()

    def write_malloc_statistics(self, typeid, size, result, varsize):
        if varsize:
            what = "malloc_varsize"
        else:
            what = "malloc"
        llop.debug_print(lltype.Void, what, typeid, " ", size, " ", result)

    def write_free_statistics(self, typeid, result):
        llop.debug_print(lltype.Void, "free", typeid, " ", result)

    def collect(self, gen=0):
        self.count_mallocs = 0
        MarkSweepGC.collect(self, gen)
