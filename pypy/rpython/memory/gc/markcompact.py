
import time

from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup
from pypy.rpython.memory.gc.base import MovingGCBase
from pypy.rlib.debug import ll_assert
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rpython.memory.support import get_address_stack, get_address_deque
from pypy.rpython.memory.support import AddressDict
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.memory.gcheader import GCHeaderBuilder

first_gcflag = 1 << 16
GCFLAG_MARKBIT = first_gcflag << 0
GCFLAG_HASHTAKEN = first_gcflag << 1      # someone already asked for the hash
GCFLAG_HASHFIELD = first_gcflag << 2      # we have an extra hash field

memoryError = MemoryError()

# Mark'n'compact garbage collector
#
# main point of this GC is to save as much memory as possible
# (not to be worse than semispace), but avoid having peaks of
# memory during collection. Inspired, at least partly by squeak's
# garbage collector

# so, the idea as now is:

# this gc works more or less like semispace, but has some essential
# differencies. The main difference is that we have separate phases of
# marking and assigning pointers, hence order of objects is preserved.
# This means we can reuse the same space if it did not grow enough.
# More importantly, in case we need to resize space we can copy it bit by
# bit, hence avoiding double memory consumption at peak times

# so the algorithm itself is performed in 3 stages (module weakrefs and
# finalizers)

# 1. We mark alive objects
# 2. We walk all objects and assign forward pointers in the same order,
#    also updating all references
# 3. We compact the space by moving. In case we move to the same space,
#    we use arena_new_view trick, which looks like new space to tests,
#    but compiles to the same pointer. Also we use raw_memmove in case
#    objects overlap.

# Exact algorithm for space resizing: we keep allocated more space than needed
# (2x, can be even more), but it's full of zeroes. After each collection,
# we bump next_collect_after which is a marker where to start each collection.
# It should be exponential (but less than 2) from the size occupied by objects

# field optimization - we don't need forward pointer and flags at the same
# time. Instead we copy list of tids when we know how many objects are alive
# and store forward pointer there.


# in case we need to grow space, we use
# current_space_size * FREE_SPACE_MULTIPLIER / FREE_SPACE_DIVIDER + needed
FREE_SPACE_MULTIPLIER = 3
FREE_SPACE_DIVIDER = 2
FREE_SPACE_ADD = 256
# XXX adjust
GC_CLEARANCE = 32*1024

TID_TYPE = rffi.USHORT
BYTES_PER_TID = rffi.sizeof(TID_TYPE)


class MarkCompactGC(MovingGCBase):
    HDR = lltype.Struct('header', ('tid', lltype.Signed))
    typeid_is_in_field = 'tid'
    withhash_flag_is_in_field = 'tid', GCFLAG_HASHFIELD
    # ^^^ all prebuilt objects have GCFLAG_HASHTAKEN, but only some have
    #     GCFLAG_HASHFIELD (and then they are one word longer).
    TID_BACKUP = lltype.Array(TID_TYPE, hints={'nolength':True})
    WEAKREF_OFFSETS = lltype.Array(lltype.Signed)


    TRANSLATION_PARAMS = {'space_size': 8*1024*1024} # XXX adjust

    malloc_zero_filled = True
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    first_unused_gcflag = first_gcflag << 3
    total_collection_time = 0.0
    total_collection_count = 0

    def __init__(self, config, chunk_size=DEFAULT_CHUNK_SIZE, space_size=4096):
        import py; py.test.skip("Disabled for now, sorry")
        self.param_space_size = space_size
        MovingGCBase.__init__(self, config, chunk_size)

    def setup(self):
        self.space_size = self.param_space_size
        self.next_collect_after = self.param_space_size/2 # whatever...

        if self.config.gcconfig.debugprint:
            self.program_start_time = time.time()
        self.space = llarena.arena_malloc(self.space_size, True)
        ll_assert(bool(self.space), "couldn't allocate arena")
        self.free = self.space
        self.top_of_space = self.space + self.next_collect_after
        MovingGCBase.setup(self)
        self.objects_with_finalizers = self.AddressDeque()
        self.objects_with_weakrefs = self.AddressStack()
        self.tid_backup = lltype.nullptr(self.TID_BACKUP)

    def init_gc_object(self, addr, typeid16, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = self.combine(typeid16, flags)

    def init_gc_object_immortal(self, addr, typeid16, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        flags |= GCFLAG_HASHTAKEN
        hdr.tid = self.combine(typeid16, flags)
        # XXX we can store forward_ptr to itself, if we fix C backend
        # so that get_forwarding_address(obj) returns
        # obj itself if obj is a prebuilt object

    def malloc_fixedsize_clear(self, typeid16, size, can_collect,
                               has_finalizer=False, contains_weakptr=False):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self.free
        if raw_malloc_usage(totalsize) > self.top_of_space - result:
            result = self.obtain_free_space(totalsize)
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid16)
        self.free += totalsize
        if has_finalizer:
            self.objects_with_finalizers.append(result + size_gc_header)
        if contains_weakptr:
            self.objects_with_weakrefs.append(result + size_gc_header)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)
    
    def malloc_varsize_clear(self, typeid16, length, size, itemsize,
                             offset_to_length, can_collect):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size
        try:
            varsize = ovfcheck(itemsize * length)
            totalsize = ovfcheck(nonvarsize + varsize)
        except OverflowError:
            raise memoryError
        result = self.free
        if raw_malloc_usage(totalsize) > self.top_of_space - result:
            result = self.obtain_free_space(totalsize)
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid16)
        (result + size_gc_header + offset_to_length).signed[0] = length
        self.free = result + llarena.round_up_for_allocation(totalsize)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    def obtain_free_space(self, totalsize):
        # a bit of tweaking to maximize the performance and minimize the
        # amount of code in an inlined version of malloc_fixedsize_clear()
        if not self.try_obtain_free_space(totalsize):
            raise memoryError
        return self.free
    obtain_free_space._dont_inline_ = True

    def try_obtain_free_space(self, needed):
        needed = raw_malloc_usage(needed)
        while 1:
            self.markcompactcollect(needed)
            missing = needed - (self.top_of_space - self.free)
            if missing < 0:
                return True

    def new_space_size(self, occupied, needed):
        res = (occupied * FREE_SPACE_MULTIPLIER /
               FREE_SPACE_DIVIDER + FREE_SPACE_ADD + needed)
        # align it to 4096, which is somewhat around page size
        return ((res/4096) + 1) * 4096

    def double_space_size(self, minimal_size):
        while self.space_size <= minimal_size:
            self.space_size *= 2
        toaddr = llarena.arena_malloc(self.space_size, True)
        return toaddr

    def compute_alive_objects(self):
        fromaddr = self.space
        addraftercollect = self.space
        num = 1
        while fromaddr < self.free:
            size_gc_header = self.gcheaderbuilder.size_gc_header
            tid = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR)).tid
            obj = fromaddr + size_gc_header
            objsize = self.get_size(obj)
            objtotalsize = size_gc_header + objsize
            if self.marked(obj):
                copy_has_hash_field = ((tid & GCFLAG_HASHFIELD) != 0 or
                                       ((tid & GCFLAG_HASHTAKEN) != 0 and
                                        addraftercollect < fromaddr))
                addraftercollect += raw_malloc_usage(objtotalsize)
                if copy_has_hash_field:
                    addraftercollect += llmemory.sizeof(lltype.Signed)
            num += 1
            fromaddr += objtotalsize
            if tid & GCFLAG_HASHFIELD:
                fromaddr += llmemory.sizeof(lltype.Signed)
        ll_assert(addraftercollect <= fromaddr,
                  "markcompactcollect() is trying to increase memory usage")
        self.totalsize_of_objs = addraftercollect - self.space
        return num

    def collect(self, gen=0):
        self.markcompactcollect()
    
    def markcompactcollect(self, needed=0):
        start_time = self.debug_collect_start()
        self.debug_check_consistency()
        self.to_see = self.AddressStack()
        self.mark_roots_recursively()
        if (self.objects_with_finalizers.non_empty() or
            self.run_finalizers.non_empty()):
            self.mark_objects_with_finalizers()
            self._trace_and_mark()
        self.to_see.delete()
        num_of_alive_objs = self.compute_alive_objects()
        size_of_alive_objs = self.totalsize_of_objs
        totalsize = self.new_space_size(size_of_alive_objs, needed +
                                        num_of_alive_objs * BYTES_PER_TID)
        tid_backup_size = (llmemory.sizeof(self.TID_BACKUP, 0) +
                           llmemory.sizeof(TID_TYPE) * num_of_alive_objs)
        used_space_now = self.next_collect_after + raw_malloc_usage(tid_backup_size)
        if totalsize >= self.space_size or used_space_now >= self.space_size:
            toaddr = self.double_space_size(totalsize)
            llarena.arena_reserve(toaddr + size_of_alive_objs, tid_backup_size)
            self.tid_backup = llmemory.cast_adr_to_ptr(
                toaddr + size_of_alive_objs,
                lltype.Ptr(self.TID_BACKUP))
            resizing = True
        else:
            toaddr = llarena.arena_new_view(self.space)
            llarena.arena_reserve(self.top_of_space, tid_backup_size)
            self.tid_backup = llmemory.cast_adr_to_ptr(
                self.top_of_space,
                lltype.Ptr(self.TID_BACKUP))
            resizing = False
        self.next_collect_after = totalsize
        weakref_offsets = self.collect_weakref_offsets()
        finaladdr = self.update_forward_pointers(toaddr, num_of_alive_objs)
        if (self.run_finalizers.non_empty() or
            self.objects_with_finalizers.non_empty()):
            self.update_run_finalizers()
        if self.objects_with_weakrefs.non_empty():
            self.invalidate_weakrefs(weakref_offsets)
        self.update_objects_with_id()
        self.compact(resizing)
        if not resizing:
            size = toaddr + self.space_size - finaladdr
            llarena.arena_reset(finaladdr, size, True)
        else:
            if we_are_translated():
                # because we free stuff already in raw_memmove, we
                # would get double free here. Let's free it anyway
                llarena.arena_free(self.space)
            llarena.arena_reset(toaddr + size_of_alive_objs, tid_backup_size,
                                True)
        self.space        = toaddr
        self.free         = finaladdr
        self.top_of_space = toaddr + self.next_collect_after
        self.debug_check_consistency()
        self.tid_backup = lltype.nullptr(self.TID_BACKUP)
        if self.run_finalizers.non_empty():
            self.execute_finalizers()
        self.debug_collect_finish(start_time)
        
    def collect_weakref_offsets(self):
        weakrefs = self.objects_with_weakrefs
        new_weakrefs = self.AddressStack()
        weakref_offsets = lltype.malloc(self.WEAKREF_OFFSETS,
                                        weakrefs.length(), flavor='raw')
        i = 0
        while weakrefs.non_empty():
            obj = weakrefs.pop()
            offset = self.weakpointer_offset(self.get_type_id(obj))
            weakref_offsets[i] = offset
            new_weakrefs.append(obj)
            i += 1
        self.objects_with_weakrefs = new_weakrefs
        weakrefs.delete()
        return weakref_offsets

    def debug_collect_start(self):
        if self.config.gcconfig.debugprint:
            llop.debug_print(lltype.Void)
            llop.debug_print(lltype.Void,
                             ".----------- Full collection ------------------")
            start_time = time.time()
            return start_time 

    def debug_collect_finish(self, start_time):
        if self.config.gcconfig.debugprint:
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.total_collection_time += elapsed_time
            self.total_collection_count += 1
            total_program_time = end_time - self.program_start_time
            ct = self.total_collection_time
            cc = self.total_collection_count
            llop.debug_print(lltype.Void,
                             "| number of collections so far       ", 
                             cc)
            llop.debug_print(lltype.Void,
                             "| total collections per second:      ",
                             cc / total_program_time)
            llop.debug_print(lltype.Void,
                             "| total time in markcompact-collect: ",
                             ct, "seconds")
            llop.debug_print(lltype.Void,
                             "| percentage collection<->total time:",
                             ct * 100.0 / total_program_time, "%")
            llop.debug_print(lltype.Void,
                             "`----------------------------------------------")


    def update_run_finalizers(self):
        run_finalizers = self.AddressDeque()
        while self.run_finalizers.non_empty():
            obj = self.run_finalizers.popleft()
            run_finalizers.append(self.get_forwarding_address(obj))
        self.run_finalizers.delete()
        self.run_finalizers = run_finalizers
        objects_with_finalizers = self.AddressDeque()
        while self.objects_with_finalizers.non_empty():
            obj = self.objects_with_finalizers.popleft()
            objects_with_finalizers.append(self.get_forwarding_address(obj))
        self.objects_with_finalizers.delete()
        self.objects_with_finalizers = objects_with_finalizers

    def header(self, addr):
        # like header(), but asserts that we have a normal header
        hdr = MovingGCBase.header(self, addr)
        if not we_are_translated():
            assert isinstance(hdr.tid, llgroup.CombinedSymbolic)
        return hdr

    def header_forwarded(self, addr):
        # like header(), but asserts that we have a forwarding header
        hdr = MovingGCBase.header(self, addr)
        if not we_are_translated():
            assert isinstance(hdr.tid, int)
        return hdr

    def combine(self, typeid16, flags):
        return llop.combine_ushort(lltype.Signed, typeid16, flags)

    def get_type_id(self, addr):
        tid = self.header(addr).tid
        return llop.extract_ushort(rffi.USHORT, tid)

    def mark_roots_recursively(self):
        self.root_walker.walk_roots(
            MarkCompactGC._mark_root_recursively,  # stack roots
            MarkCompactGC._mark_root_recursively,  # static in prebuilt non-gc structures
            MarkCompactGC._mark_root_recursively)  # static in prebuilt gc objects
        self._trace_and_mark()

    def _trace_and_mark(self):
        # XXX depth-first tracing... it can consume a lot of rawmalloced
        # memory for very long stacks in some cases
        while self.to_see.non_empty():
            obj = self.to_see.pop()
            self.trace(obj, self._mark_obj, None)

    def _mark_obj(self, pointer, ignored):
        obj = pointer.address[0]
        if self.marked(obj):
            return
        self.mark(obj)
        self.to_see.append(obj)

    def _mark_root_recursively(self, root):
        self.mark(root.address[0])
        self.to_see.append(root.address[0])

    def mark(self, obj):
        self.header(obj).tid |= GCFLAG_MARKBIT

    def marked(self, obj):
        return self.header(obj).tid & GCFLAG_MARKBIT

    def update_forward_pointers(self, toaddr, num_of_alive_objs):
        self.base_forwarding_addr = toaddr
        fromaddr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        i = 0
        while fromaddr < self.free:
            hdr = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR))
            obj = fromaddr + size_gc_header
            objsize = self.get_size(obj)
            totalsize = size_gc_header + objsize
            if not self.marked(obj):
                self.set_null_forwarding_address(obj, i)
            else:
                llarena.arena_reserve(toaddr, totalsize)
                self.set_forwarding_address(obj, toaddr, i)
                toaddr += totalsize
            i += 1
            fromaddr += totalsize

        # now update references
        self.root_walker.walk_roots(
            MarkCompactGC._update_root,  # stack roots
            MarkCompactGC._update_root,  # static in prebuilt non-gc structures
            MarkCompactGC._update_root)  # static in prebuilt gc objects
        fromaddr = self.space
        i = 0
        while fromaddr < self.free:
            hdr = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR))
            obj = fromaddr + size_gc_header
            objsize = self.get_size_from_backup(obj, i)
            totalsize = size_gc_header + objsize
            if not self.surviving(obj):
                pass
            else:
                self.trace_with_backup(obj, self._update_ref, i)
            fromaddr += totalsize
            i += 1
        return toaddr

    def trace_with_backup(self, obj, callback, arg):
        """Enumerate the locations inside the given obj that can contain
        GC pointers.  For each such location, callback(pointer, arg) is
        called, where 'pointer' is an address inside the object.
        Typically, 'callback' is a bound method and 'arg' can be None.
        """
        typeid = self.get_typeid_from_backup(arg)
        if self.is_gcarrayofgcptr(typeid):
            # a performance shortcut for GcArray(gcptr)
            length = (obj + llmemory.gcarrayofptr_lengthoffset).signed[0]
            item = obj + llmemory.gcarrayofptr_itemsoffset
            while length > 0:
                if self.points_to_valid_gc_object(item):
                    callback(item, arg)
                item += llmemory.gcarrayofptr_singleitemoffset
                length -= 1
            return
        offsets = self.offsets_to_gc_pointers(typeid)
        i = 0
        while i < len(offsets):
            item = obj + offsets[i]
            if self.points_to_valid_gc_object(item):
                callback(item, arg)
            i += 1
        if self.has_gcptr_in_varsize(typeid):
            item = obj + self.varsize_offset_to_variable_part(typeid)
            length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
            offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
            itemlength = self.varsize_item_sizes(typeid)
            while length > 0:
                j = 0
                while j < len(offsets):
                    itemobj = item + offsets[j]
                    if self.points_to_valid_gc_object(itemobj):
                        callback(itemobj, arg)
                    j += 1
                item += itemlength
                length -= 1
    trace_with_backup._annspecialcase_ = 'specialize:arg(2)'

    def _update_root(self, pointer):
        if pointer.address[0] != NULL:
            pointer.address[0] = self.get_forwarding_address(pointer.address[0])

    def _update_ref(self, pointer, ignore):
        if pointer.address[0] != NULL:
            pointer.address[0] = self.get_forwarding_address(pointer.address[0])

    def _is_external(self, obj):
        return not (self.space <= obj < self.top_of_space)

    def get_forwarding_address(self, obj):
        if self._is_external(obj):
            return obj
        return self.get_header_forwarded_addr(obj)

    def set_null_forwarding_address(self, obj, num):
        self.backup_typeid(num, obj)
        hdr = self.header(obj)
        hdr.tid = -1          # make the object forwarded to NULL

    def set_forwarding_address(self, obj, newobjhdr, num):
        self.backup_typeid(num, obj)
        forward_offset = newobjhdr - self.base_forwarding_addr
        hdr = self.header(obj)
        hdr.tid = forward_offset     # make the object forwarded to newobj

    def restore_normal_header(self, obj, num):
        # Reverse of set_forwarding_address().
        typeid16 = self.get_typeid_from_backup(num)
        hdr = self.header_forwarded(obj)
        hdr.tid = self.combine(typeid16, 0)      # restore the normal header

    def get_header_forwarded_addr(self, obj):
        return (self.base_forwarding_addr +
                self.header_forwarded(obj).tid +
                self.gcheaderbuilder.size_gc_header)

    def surviving(self, obj):
        return self._is_external(obj) or self.header_forwarded(obj).tid != -1

    def backup_typeid(self, num, obj):
        self.tid_backup[num] = self.get_type_id(obj)

    def get_typeid_from_backup(self, num):
        return self.tid_backup[num]

    def get_size_from_backup(self, obj, num):
        typeid = self.get_typeid_from_backup(num)
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            lenaddr = obj + self.varsize_offset_to_length(typeid)
            length = lenaddr.signed[0]
            size += length * self.varsize_item_sizes(typeid)
            size = llarena.round_up_for_allocation(size)
            # XXX maybe we should parametrize round_up_for_allocation()
            # per GC; if we do, we also need to fix the call in
            # gctypelayout.encode_type_shape()
        return size

    def compact(self, resizing):
        fromaddr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        start = fromaddr
        end = fromaddr
        num = 0
        while fromaddr < self.free:
            obj = fromaddr + size_gc_header
            objsize = self.get_size_from_backup(obj, num)
            totalsize = size_gc_header + objsize
            if not self.surviving(obj): 
                # this object dies. Following line is a noop in C,
                # we clear it to make debugging easier
                llarena.arena_reset(fromaddr, totalsize, False)
            else:
                if resizing:
                    end = fromaddr
                forward_obj = self.get_header_forwarded_addr(obj)
                self.restore_normal_header(obj, num)
                if obj != forward_obj:
                    #llop.debug_print(lltype.Void, "Copying from to",
                    #                 fromaddr, forward_ptr, totalsize)
                    llmemory.raw_memmove(fromaddr,
                                         forward_obj - size_gc_header,
                                         totalsize)
                if resizing and end - start > GC_CLEARANCE:
                    diff = end - start
                    #llop.debug_print(lltype.Void, "Cleaning", start, diff)
                    diff = (diff / GC_CLEARANCE) * GC_CLEARANCE
                    #llop.debug_print(lltype.Void, "Cleaning", start, diff)
                    end = start + diff
                    if we_are_translated():
                        # XXX wuaaaaa.... those objects are freed incorrectly
                        #                 here in case of test_gc
                        llarena.arena_reset(start, diff, True)
                    start += diff
            num += 1
            fromaddr += totalsize

    def debug_check_object(self, obj):
        # not sure what to check here
        pass

    def mark_objects_with_finalizers(self):
        new_with_finalizers = self.AddressDeque()
        run_finalizers = self.run_finalizers
        new_run_finalizers = self.AddressDeque()
        while run_finalizers.non_empty():
            x = run_finalizers.popleft()
            self.mark(x)
            self.to_see.append(x)
            new_run_finalizers.append(x)
        run_finalizers.delete()
        self.run_finalizers = new_run_finalizers
        while self.objects_with_finalizers.non_empty():
            x = self.objects_with_finalizers.popleft()
            if self.marked(x):
                new_with_finalizers.append(x)
            else:
                new_run_finalizers.append(x)
                self.mark(x)
                self.to_see.append(x)
        self.objects_with_finalizers.delete()
        self.objects_with_finalizers = new_with_finalizers

    def invalidate_weakrefs(self, weakref_offsets):
        # walk over list of objects that contain weakrefs
        # if the object it references survives then update the weakref
        # otherwise invalidate the weakref
        new_with_weakref = self.AddressStack()
        i = 0
        while self.objects_with_weakrefs.non_empty():
            obj = self.objects_with_weakrefs.pop()
            if not self.surviving(obj):
                continue # weakref itself dies
            newobj = self.get_forwarding_address(obj)
            offset = weakref_offsets[i]
            pointing_to = (obj + offset).address[0]
            # XXX I think that pointing_to cannot be NULL here
            if pointing_to:
                if self.surviving(pointing_to):
                    (obj + offset).address[0] = self.get_forwarding_address(
                        pointing_to)
                    new_with_weakref.append(newobj)
                else:
                    (obj + offset).address[0] = NULL
            i += 1
        self.objects_with_weakrefs.delete()
        self.objects_with_weakrefs = new_with_weakref
        lltype.free(weakref_offsets, flavor='raw')

    def get_size_incl_hash(self, obj):
        size = self.get_size(obj)
        hdr = self.header(obj)
        if hdr.tid & GCFLAG_HASHFIELD:
            size += llmemory.sizeof(lltype.Signed)
        return size

    def identityhash(self, gcobj):
        # Unlike SemiSpaceGC.identityhash(), this function does not have
        # to care about reducing top_of_space.  The reason is as
        # follows.  When we collect, each object either moves to the
        # left or stays where it is.  If it moves to the left (and if it
        # has GCFLAG_HASHTAKEN), we can give it a hash field, and the
        # end of the new object cannot move to the right of the end of
        # the old object.  If it stays where it is, then we don't need
        # to add the hash field.  So collecting can never actually grow
        # the consumed size.
        obj = llmemory.cast_ptr_to_adr(gcobj)
        hdr = self.header(obj)
        #
        if hdr.tid & GCFLAG_HASHFIELD:  # the hash is in a field at the end
            obj += self.get_size(obj)
            return obj.signed[0]
        #
        hdr.tid |= GCFLAG_HASHTAKEN
        return llmemory.cast_adr_to_int(obj)  # direct case
