import sys
from pypy.rpython.memory.gc.semispace import SemiSpaceGC, GCFLAG_IMMORTAL
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rlib.objectmodel import free_non_gc_object
from pypy.rlib.debug import ll_assert
from pypy.rpython.lltypesystem.lloperation import llop

# The following flag is never set on young objects, i.e. the ones living
# in the nursery.  It is initially set on all prebuilt and old objects,
# and gets cleared by the write_barrier() when we write in them a
# pointer to a young object.
GCFLAG_NO_YOUNG_PTRS = SemiSpaceGC.first_unused_gcflag << 0

# The following flag is set for static roots which are not on the list
# of static roots yet, but will appear with write barrier
GCFLAG_NO_HEAP_PTRS = SemiSpaceGC.first_unused_gcflag << 1

DEBUG_PRINT = False

class GenerationGC(SemiSpaceGC):
    """A basic generational GC: it's a SemiSpaceGC with an additional
    nursery for young objects.  A write barrier is used to ensure that
    old objects that contain pointers to young objects are recorded in
    a list.
    """
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = True
    prebuilt_gc_objects_are_static_roots = False
    first_unused_gcflag = SemiSpaceGC.first_unused_gcflag << 2

    def __init__(self, chunk_size=DEFAULT_CHUNK_SIZE,
                 nursery_size=128,
                 min_nursery_size=128,
                 auto_nursery_size=False,
                 space_size=4096,
                 max_space_size=sys.maxint//2+1):
        SemiSpaceGC.__init__(self, chunk_size = chunk_size,
                             space_size = space_size,
                             max_space_size = max_space_size)
        assert min_nursery_size <= nursery_size <= space_size // 2
        self.initial_nursery_size = nursery_size
        self.auto_nursery_size = auto_nursery_size
        self.min_nursery_size = min_nursery_size
        self.old_objects_pointing_to_young = self.AddressStack()
        # ^^^ a list of addresses inside the old objects space; it
        # may contain static prebuilt objects as well.  More precisely,
        # it lists exactly the old and static objects whose
        # GCFLAG_NO_YOUNG_PTRS bit is not set.
        self.young_objects_with_weakrefs = self.AddressStack()
        self.reset_nursery()

    def setup(self):
        SemiSpaceGC.setup(self)
        self.set_nursery_size(self.initial_nursery_size)
        # the GC is fully setup now.  The rest can make use of it.
        if self.auto_nursery_size:
            newsize = nursery_size_from_env()
            if newsize <= 0:
                newsize = estimate_best_nursery_size()
            if newsize > 0:
                self.set_nursery_size(newsize)

    def reset_nursery(self):
        self.nursery      = NULL
        self.nursery_top  = NULL
        self.nursery_free = NULL

    def set_nursery_size(self, newsize):
        if newsize < self.min_nursery_size:
            newsize = self.min_nursery_size
        if newsize > self.space_size // 2:
            newsize = self.space_size // 2

        # Compute the new bounds for how large young objects can be
        # (larger objects are allocated directly old).   XXX adjust
        self.nursery_size = newsize
        self.largest_young_fixedsize = newsize // 2 - 1
        self.largest_young_var_basesize = newsize // 4 - 1
        scale = 0
        while (self.min_nursery_size << (scale+1)) <= newsize:
            scale += 1
        self.nursery_scale = scale
        if DEBUG_PRINT:
            llop.debug_print(lltype.Void, "SSS  nursery_size =", newsize)
            llop.debug_print(lltype.Void, "SSS  largest_young_fixedsize =",
                             self.largest_young_fixedsize)
            llop.debug_print(lltype.Void, "SSS  largest_young_var_basesize =",
                             self.largest_young_var_basesize)
            llop.debug_print(lltype.Void, "SSS  nursery_scale =", scale)
        # we get the following invariant:
        assert self.nursery_size >= (self.min_nursery_size << scale)

        # Force a full collect to remove the current nursery whose size
        # no longer matches the bounds that we just computed.  This must
        # be done after changing the bounds, because it might re-create
        # a new nursery (e.g. if it invokes finalizers).
        self.semispace_collect()

    def is_in_nursery(self, addr):
        return self.nursery <= addr < self.nursery_top

    def malloc_fixedsize_clear(self, typeid, size, can_collect,
                               has_finalizer=False, contains_weakptr=False):
        if (has_finalizer or not can_collect or
            raw_malloc_usage(size) > self.largest_young_fixedsize):
            ll_assert(not contains_weakptr, "wrong case for mallocing weakref")
            # "non-simple" case or object too big: don't use the nursery
            return SemiSpaceGC.malloc_fixedsize_clear(self, typeid, size,
                                                      can_collect,
                                                      has_finalizer,
                                                      contains_weakptr)
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self.nursery_free
        if raw_malloc_usage(totalsize) > self.nursery_top - result:
            result = self.collect_nursery()
        llarena.arena_reserve(result, totalsize)
        # GCFLAG_NO_YOUNG_PTRS is never set on young objs
        self.init_gc_object(result, typeid, flags=0)
        self.nursery_free = result + totalsize
        if contains_weakptr:
            self.young_objects_with_weakrefs.append(result + size_gc_header)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    def coalloc_fixedsize_clear(self, coallocator, typeid, size):
        # note: a coallocated object can never return a weakref, since the
        # coallocation analysis is done at a time where weakrefs are
        # represented as opaque objects which aren't allocated using malloc but
        # with weakref_create
        if self.is_in_nursery(coallocator):
            return self.malloc_fixedsize_clear(typeid, size,
                                               True, False, False)
        else:
            return SemiSpaceGC.malloc_fixedsize_clear(self, typeid, size,
                                                      True, False, False)

    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length, can_collect,
                             has_finalizer=False):
        # Only use the nursery if there are not too many items.
        if not raw_malloc_usage(itemsize):
            too_many_items = False
        else:
            # The following line is usually constant-folded because both
            # min_nursery_size and itemsize are constants (the latter
            # due to inlining).
            maxlength_for_minimal_nursery = (self.min_nursery_size // 4 //
                                             raw_malloc_usage(itemsize))
            
            # The actual maximum length for our nursery depends on how
            # many times our nursery is bigger than the minimal size.
            # The computation is done in this roundabout way so that
            # only the only remaining computation is the following
            # shift.
            maxlength = maxlength_for_minimal_nursery << self.nursery_scale
            too_many_items = length > maxlength

        if (has_finalizer or not can_collect or
            too_many_items or
            raw_malloc_usage(size) > self.largest_young_var_basesize):
            return SemiSpaceGC.malloc_varsize_clear(self, typeid, length, size,
                                                    itemsize, offset_to_length,
                                                    can_collect, has_finalizer)
        # with the above checks we know now that totalsize cannot be more
        # than about half of the nursery size; in particular, the + and *
        # cannot overflow
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size + itemsize * length
        result = self.nursery_free
        if raw_malloc_usage(totalsize) > self.nursery_top - result:
            result = self.collect_nursery()
        llarena.arena_reserve(result, totalsize)
        # GCFLAG_NO_YOUNG_PTRS is never set on young objs
        self.init_gc_object(result, typeid, flags=0)
        (result + size_gc_header + offset_to_length).signed[0] = length
        self.nursery_free = result + llarena.round_up_for_allocation(totalsize)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    def coalloc_varsize_clear(self, coallocator, typeid,
                              length, size, itemsize,
                              offset_to_length):
        if self.is_in_nursery(coallocator):
            return self.malloc_varsize_clear(typeid, length, size, itemsize,
                                             offset_to_length, True, False)
        else:
            return SemiSpaceGC.malloc_varsize_clear(self, typeid, length, size,
                                                    itemsize, offset_to_length,
                                                    True, False)

    # override the init_gc_object methods to change the default value of 'flags',
    # used by objects that are directly created outside the nursery by the SemiSpaceGC.
    # These objects must have the GCFLAG_NO_YOUNG_PTRS flag set immediately.
    def init_gc_object(self, addr, typeid, flags=GCFLAG_NO_YOUNG_PTRS):
        SemiSpaceGC.init_gc_object(self, addr, typeid, flags)

    def init_gc_object_immortal(self, addr, typeid,
                                flags=GCFLAG_NO_YOUNG_PTRS|GCFLAG_NO_HEAP_PTRS):
        SemiSpaceGC.init_gc_object_immortal(self, addr, typeid, flags)

    def semispace_collect(self, size_changing=False):
        self.reset_young_gcflags() # we are doing a full collection anyway
        self.weakrefs_grow_older()
        self.reset_nursery()
        if DEBUG_PRINT:
            llop.debug_print(lltype.Void, "major collect, size changing", size_changing)
        SemiSpaceGC.semispace_collect(self, size_changing)
        if DEBUG_PRINT and not size_changing:
            llop.debug_print(lltype.Void, "percent survived", float(self.free - self.tospace) / self.space_size)
            

    def trace_and_copy(self, obj):
        # during a full collect, all objects copied might come from the nursery and
        # so must have this flag set:
        self.header(obj).tid |= GCFLAG_NO_YOUNG_PTRS
        SemiSpaceGC.trace_and_copy(self, obj)
        # history: this was missing and caused an object to become old but without the
        # flag set.  Such an object is bogus in the sense that the write_barrier doesn't
        # work on it.  So it can eventually contain a ptr to a young object but we didn't
        # know about it.  That ptr was not updated in the next minor collect... boom at
        # the next usage.

    def reset_young_gcflags(self):
        oldlist = self.old_objects_pointing_to_young
        while oldlist.non_empty():
            obj = oldlist.pop()
            hdr = self.header(obj)
            hdr.tid |= GCFLAG_NO_YOUNG_PTRS

    def weakrefs_grow_older(self):
        while self.young_objects_with_weakrefs.non_empty():
            obj = self.young_objects_with_weakrefs.pop()
            self.objects_with_weakrefs.append(obj)

    def collect_nursery(self):
        if self.nursery_size > self.top_of_space - self.free:
            # the semispace is running out, do a full collect
            self.obtain_free_space(self.nursery_size)
            ll_assert(self.nursery_size <= self.top_of_space - self.free,
                         "obtain_free_space failed to do its job")
        if self.nursery:
            if DEBUG_PRINT:
                llop.debug_print(lltype.Void, "minor collect")
            # a nursery-only collection
            scan = beginning = self.free
            self.collect_oldrefs_to_nursery()
            self.collect_roots_in_nursery()
            scan = self.scan_objects_just_copied_out_of_nursery(scan)
            # at this point, all static and old objects have got their
            # GCFLAG_NO_YOUNG_PTRS set again by trace_and_drag_out_of_nursery
            if self.young_objects_with_weakrefs.non_empty():
                self.invalidate_young_weakrefs()
            self.notify_objects_just_moved()
            # mark the nursery as free and fill it with zeroes again
            llarena.arena_reset(self.nursery, self.nursery_size, True)
            if DEBUG_PRINT:
                llop.debug_print(lltype.Void, "percent survived:", float(scan - beginning) / self.nursery_size)
        else:
            # no nursery - this occurs after a full collect, triggered either
            # just above or by some previous non-nursery-based allocation.
            # Grab a piece of the current space for the nursery.
            self.nursery = self.free
            self.nursery_top = self.nursery + self.nursery_size
            self.free = self.nursery_top
        self.nursery_free = self.nursery
        return self.nursery_free

    # NB. we can use self.copy() to move objects out of the nursery,
    # but only if the object was really in the nursery.

    def collect_oldrefs_to_nursery(self):
        # Follow the old_objects_pointing_to_young list and move the
        # young objects they point to out of the nursery.
        count = 0
        oldlist = self.old_objects_pointing_to_young
        while oldlist.non_empty():
            count += 1
            obj = oldlist.pop()
            self.trace_and_drag_out_of_nursery(obj)
        if DEBUG_PRINT:
            llop.debug_print(lltype.Void, "collect_oldrefs_to_nursery", count)

    def collect_roots_in_nursery(self):
        # we don't need to trace prebuilt GcStructs during a minor collect:
        # if a prebuilt GcStruct contains a pointer to a young object,
        # then the write_barrier must have ensured that the prebuilt
        # GcStruct is in the list self.old_objects_pointing_to_young.
        self.root_walker.walk_roots(
            GenerationGC._collect_root_in_nursery,  # stack roots
            GenerationGC._collect_root_in_nursery,  # static in prebuilt non-gc
            None)                                   # static in prebuilt gc

    def _collect_root_in_nursery(self, root):
        obj = root.address[0]
        if self.is_in_nursery(obj):
            root.address[0] = self.copy(obj)

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
        self.header(obj).tid |= GCFLAG_NO_YOUNG_PTRS
        self.trace(obj, self._trace_drag_out, None)

    def _trace_drag_out(self, pointer, ignored):
        if self.is_in_nursery(pointer.address[0]):
            pointer.address[0] = self.copy(pointer.address[0])

    def invalidate_young_weakrefs(self):
        # walk over the list of objects that contain weakrefs and are in the
        # nursery.  if the object it references survives then update the
        # weakref; otherwise invalidate the weakref
        while self.young_objects_with_weakrefs.non_empty():
            obj = self.young_objects_with_weakrefs.pop()
            if not self.is_forwarded(obj):
                continue # weakref itself dies
            obj = self.get_forwarding_address(obj)
            offset = self.weakpointer_offset(self.get_type_id(obj))
            pointing_to = (obj + offset).address[0]
            if self.is_in_nursery(pointing_to):
                if self.is_forwarded(pointing_to):
                    (obj + offset).address[0] = self.get_forwarding_address(
                        pointing_to)
                else:
                    (obj + offset).address[0] = NULL
                    continue    # no need to remember this weakref any longer
            self.objects_with_weakrefs.append(obj)

    def write_barrier(self, oldvalue, newvalue, addr_struct):
        if self.header(addr_struct).tid & GCFLAG_NO_YOUNG_PTRS:
            self.remember_young_pointer(addr_struct, newvalue)

    def append_to_static_roots(self, pointer, arg):
        self.root_walker.append_static_root(pointer)

    def move_to_static_roots(self, addr_struct):
        objhdr = self.header(addr_struct)
        objhdr.tid &= ~GCFLAG_NO_HEAP_PTRS
        self.trace(addr_struct, self.append_to_static_roots, None)

    def remember_young_pointer(self, addr_struct, addr):
        ll_assert(not self.is_in_nursery(addr_struct),
                     "nursery object with GCFLAG_NO_YOUNG_PTRS")
        oldhdr = self.header(addr_struct)
        if self.is_in_nursery(addr):
            self.old_objects_pointing_to_young.append(addr_struct)
            oldhdr.tid &= ~GCFLAG_NO_YOUNG_PTRS
        if oldhdr.tid & GCFLAG_NO_HEAP_PTRS:
            self.move_to_static_roots(addr_struct)
    remember_young_pointer._dont_inline_ = True

# ____________________________________________________________

import os

def nursery_size_from_env():
    value = os.environ.get('PYPY_GENERATIONGC_NURSERY')
    if value:
        if value[-1] in 'kK':
            factor = 1024
            value = value[:-1]
        else:
            factor = 1
        try:
            return int(value) * factor
        except ValueError:
            pass
    return -1

def best_nursery_size_for_L2cache(L2cache):
    if DEBUG_PRINT:
        llop.debug_print(lltype.Void, "CCC  L2cache =", L2cache)
    # Heuristically, the best nursery size to choose is about half
    # of the L2 cache.  XXX benchmark some more.
    return L2cache // 2


if sys.platform == 'linux2':
    def estimate_best_nursery_size():
        """Try to estimate the best nursery size at run-time, depending
        on the machine we are running on.
        """
        L2cache = sys.maxint
        try:
            fd = os.open('/proc/cpuinfo', os.O_RDONLY, 0644)
            try:
                data = []
                while True:
                    buf = os.read(fd, 4096)
                    if not buf:
                        break
                    data.append(buf)
            finally:
                os.close(fd)
        except OSError:
            pass
        else:
            data = ''.join(data)
            linepos = 0
            while True:
                start = findend(data, '\ncache size', linepos)
                if start < 0:
                    break    # done
                linepos = findend(data, '\n', start)
                if linepos < 0:
                    break    # no end-of-line??
                # *** data[start:linepos] == "   : 2048 KB\n"
                start = skipspace(data, start)
                if data[start] != ':':
                    continue
                # *** data[start:linepos] == ": 2048 KB\n"
                start = skipspace(data, start + 1)
                # *** data[start:linepos] == "2048 KB\n"
                end = start
                while '0' <= data[end] <= '9':
                    end += 1
                # *** data[start:end] == "2048"
                if start == end:
                    continue
                number = int(data[start:end])
                # *** data[end:linepos] == " KB\n"
                end = skipspace(data, end)
                if data[end] not in ('K', 'k'):    # assume kilobytes for now
                    continue
                number = number * 1024
                # for now we look for the smallest of the L2 caches of the CPUs
                if number < L2cache:
                    L2cache = number

        if L2cache < sys.maxint:
            return best_nursery_size_for_L2cache(L2cache)
        else:
            # Print a warning even in non-debug builds
            llop.debug_print(lltype.Void,
                "Warning: cannot find your CPU L2 cache size in /proc/cpuinfo")
            return -1

    def findend(data, pattern, pos):
        pos = data.find(pattern, pos)
        if pos < 0:
            return -1
        return pos + len(pattern)

    def skipspace(data, pos):
        while data[pos] in (' ', '\t'):
            pos += 1
        return pos

elif sys.platform == 'darwin':
    from pypy.rpython.lltypesystem import lltype, rffi

    sysctlbyname = rffi.llexternal('sysctlbyname',
                                   [rffi.CCHARP, rffi.VOIDP, rffi.SIZE_TP,
                                    rffi.VOIDP, rffi.SIZE_T],
                                   rffi.INT)

    def estimate_best_nursery_size():
        """Try to estimate the best nursery size at run-time, depending
        on the machine we are running on.
        """
        L2cache = 0
        l2cache_p = lltype.malloc(rffi.LONGLONGP.TO, 1, flavor='raw')
        try:
            len_p = lltype.malloc(rffi.SIZE_TP.TO, 1, flavor='raw')
            try:
                size = rffi.sizeof(rffi.LONGLONG)
                l2cache_p[0] = rffi.cast(rffi.LONGLONG, 0)
                len_p[0] = rffi.cast(rffi.SIZE_T, size)
                result = sysctlbyname("hw.l2cachesize",
                                      rffi.cast(rffi.VOIDP, l2cache_p),
                                      len_p,
                                      lltype.nullptr(rffi.VOIDP.TO), 
                                      rffi.cast(rffi.SIZE_T, 0))
                if (rffi.cast(lltype.Signed, result) == 0 and
                    rffi.cast(lltype.Signed, len_p[0]) == size):
                    L2cache = rffi.cast(lltype.Signed, l2cache_p[0])
                    if rffi.cast(rffi.LONGLONG, L2cache) != l2cache_p[0]:
                        L2cache = 0    # overflow!
            finally:
                lltype.free(len_p, flavor='raw')
        finally:
            lltype.free(l2cache_p, flavor='raw')
        if L2cache > 0:
            return best_nursery_size_for_L2cache(L2cache)
        else:
            # Print a warning even in non-debug builds
            llop.debug_print(lltype.Void,
                "Warning: cannot find your CPU L2 cache size with sysctl()")
            return -1

else:
    def estimate_best_nursery_size():
        return -1     # XXX implement me for other platforms
