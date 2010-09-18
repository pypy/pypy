import sys
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.memory.gc.base import GCBase, MovingGCBase
from pypy.rpython.memory.gc import minimarkpage, base, generation
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rlib.rarithmetic import ovfcheck, LONG_BIT, intmask, r_uint
from pypy.rlib.debug import ll_assert, debug_print, debug_start, debug_stop
from pypy.rlib.objectmodel import we_are_translated

WORD = LONG_BIT // 8
NULL = llmemory.NULL

first_gcflag = 1 << (LONG_BIT//2)

# The following flag is never set on young objects, i.e. the ones living
# in the nursery.  It is initially set on all prebuilt and old objects,
# and gets cleared by the write_barrier() when we write in them a
# pointer to a young object.
GCFLAG_NO_YOUNG_PTRS = first_gcflag << 0

# The following flag is set on some prebuilt objects.  The flag is set
# unless the object is already listed in 'prebuilt_root_objects'.
# When a pointer is written inside an object with GCFLAG_NO_HEAP_PTRS
# set, the write_barrier clears the flag and adds the object to
# 'prebuilt_root_objects'.
GCFLAG_NO_HEAP_PTRS = first_gcflag << 1

# The following flag is set on surviving objects during a major collection.
GCFLAG_VISITED      = first_gcflag << 2

# The following flag is set on nursery objects of which we asked the id
# or the identityhash.  It means that a space of the size of the object
# has already been allocated in the nonmovable part.  The same flag is
# abused to mark prebuilt objects whose hash has been taken during
# translation and is statically recorded.
GCFLAG_HAS_SHADOW   = first_gcflag << 3

# The following flag is set temporarily on some objects during a major
# collection.  See pypy/doc/discussion/finalizer-order.txt
GCFLAG_FINALIZATION_ORDERING = first_gcflag << 4


FORWARDSTUB = lltype.GcStruct('forwarding_stub',
                              ('forw', llmemory.Address))
FORWARDSTUBPTR = lltype.Ptr(FORWARDSTUB)


# ____________________________________________________________

class MiniMarkGC(MovingGCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = True
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True    # xxx experiment with False

    # All objects start with a HDR, i.e. with a field 'tid' which contains
    # a word.  This word is divided in two halves: the lower half contains
    # the typeid, and the upper half contains various flags, as defined
    # by GCFLAG_xxx above.
    HDR = lltype.Struct('header', ('tid', lltype.Signed))
    typeid_is_in_field = 'tid'
    withhash_flag_is_in_field = 'tid', GCFLAG_HAS_SHADOW
    # ^^^ prebuilt objects may have the flag GCFLAG_HAS_SHADOW;
    #     then they are one word longer, the extra word storing the hash.


    # During a minor collection, the objects in the nursery that are
    # moved outside are changed in-place: their header is replaced with
    # the value -1, and the following word is set to the address of
    # where the object was moved.  This means that all objects in the
    # nursery need to be at least 2 words long, but objects outside the
    # nursery don't need to.
    minimal_size_in_nursery = (
        llmemory.sizeof(HDR) + llmemory.sizeof(llmemory.Address))


    TRANSLATION_PARAMS = {
        # Automatically adjust the size of the nursery and the
        # 'major_collection_threshold' from the environment.  For
        # 'nursery_size' it will look it up in the env var
        # PYPY_GC_NURSERY and fall back to half the size of
        # the L2 cache.  For 'major_collection_threshold' it will look
        # it up in the env var PYPY_GC_MAJOR_COLLECT.  It also sets
        # 'max_heap_size' to PYPY_GC_MAX.
        "read_from_env": True,

        # The size of the nursery.  Note that this is only used as a
        # fall-back number.
        "nursery_size": 896*1024,

        # The system page size.  Like obmalloc.c, we assume that it is 4K,
        # which is OK for most systems.
        "page_size": 4096,

        # The size of an arena.  Arenas are groups of pages allocated
        # together.
        "arena_size": 65536*WORD,

        # The maximum size of an object allocated compactly.  All objects
        # that are larger are just allocated with raw_malloc().  The value
        # chosen here is enough for a unicode string of length 56 (on 64-bits)
        # or 60 (on 32-bits).  See rlib.rstring.INIT_SIZE.
        "small_request_threshold": 256-WORD,

        # Full collection threshold: after a major collection, we record
        # the total size consumed; and after every minor collection, if the
        # total size is now more than 'major_collection_threshold' times,
        # we trigger the next major collection.
        "major_collection_threshold": 1.82,
        }

    def __init__(self, config, chunk_size=DEFAULT_CHUNK_SIZE,
                 read_from_env=False,
                 nursery_size=32*WORD,
                 page_size=16*WORD,
                 arena_size=64*WORD,
                 small_request_threshold=5*WORD,
                 major_collection_threshold=2.5,
                 ArenaCollectionClass=None):
        MovingGCBase.__init__(self, config, chunk_size)
        assert small_request_threshold % WORD == 0
        self.read_from_env = read_from_env
        self.nursery_size = nursery_size
        self.small_request_threshold = small_request_threshold
        self.major_collection_threshold = major_collection_threshold
        self.num_major_collects = 0
        self.max_heap_size = 0.0
        self.max_heap_size_already_raised = False
        #
        self.nursery      = NULL
        self.nursery_free = NULL
        self.nursery_top  = NULL
        #
        # The ArenaCollection() handles the nonmovable objects allocation.
        if ArenaCollectionClass is None:
            ArenaCollectionClass = minimarkpage.ArenaCollection
        self.ac = ArenaCollectionClass(arena_size, page_size,
                                       small_request_threshold)
        #
        # Used by minor collection: a list of non-young objects that
        # (may) contain a pointer to a young object.  Populated by
        # the write barrier.
        self.old_objects_pointing_to_young = self.AddressStack()
        #
        # A list of all prebuilt GC objects that contain pointers to the heap
        self.prebuilt_root_objects = self.AddressStack()
        #
        self._init_writebarrier_logic()


    def setup(self):
        """Called at run-time to initialize the GC."""
        #
        # Hack: MovingGCBase.setup() sets up stuff related to id(), which
        # we implement differently anyway.  So directly call GCBase.setup().
        GCBase.setup(self)
        #
        # A list of all raw_malloced objects (the objects too large)
        self.rawmalloced_objects = self.AddressStack()
        self.rawmalloced_total_size = r_uint(0)
        #
        # A list of all objects with finalizers (never in the nursery).
        self.objects_with_finalizers = self.AddressDeque()
        #
        # Two lists of the objects with weakrefs.  No weakref can be an
        # old object weakly pointing to a young object: indeed, weakrefs
        # are immutable so they cannot point to an object that was
        # created after it.
        self.young_objects_with_weakrefs = self.AddressStack()
        self.old_objects_with_weakrefs = self.AddressStack()
        #
        # Support for id and identityhash: map nursery objects with
        # GCFLAG_HAS_SHADOW to their future location at the next
        # minor collection.
        self.young_objects_shadows = self.AddressDict()
        #
        # Allocate a nursery.  In case of auto_nursery_size, start by
        # allocating a very small nursery, enough to do things like look
        # up the env var, which requires the GC; and then really
        # allocate the nursery of the final size.
        if not self.read_from_env:
            self.allocate_nursery()
        else:
            #
            defaultsize = self.nursery_size
            minsize = 18 * self.small_request_threshold
            self.nursery_size = minsize
            self.allocate_nursery()
            #
            # From there on, the GC is fully initialized and the code
            # below can use it
            newsize = base.read_from_env('PYPY_GC_NURSERY')
            if newsize <= 0:
                newsize = generation.estimate_best_nursery_size()
                if newsize <= 0:
                    newsize = defaultsize
            #
            major_coll = base.read_float_from_env('PYPY_GC_MAJOR_COLLECT')
            if major_coll >= 1.0:
                self.major_collection_threshold = major_coll
            #
            max_heap_size = base.read_uint_from_env('PYPY_GC_MAX')
            if max_heap_size > 0:
                self.max_heap_size = float(max_heap_size)
            #
            self.minor_collection()    # to empty the nursery
            llarena.arena_free(self.nursery)
            self.nursery_size = max(newsize, minsize)
            self.allocate_nursery()


    def allocate_nursery(self):
        debug_start("gc-set-nursery-size")
        debug_print("nursery size:", self.nursery_size)
        # the start of the nursery: we actually allocate a tiny bit more for
        # the nursery than really needed, to simplify pointer arithmetic
        # in malloc_fixedsize_clear().
        extra = self.small_request_threshold
        self.nursery = llarena.arena_malloc(self.nursery_size + extra, True)
        if not self.nursery:
            raise MemoryError("cannot allocate nursery")
        # the current position in the nursery:
        self.nursery_free = self.nursery
        # the end of the nursery:
        self.nursery_top = self.nursery + self.nursery_size
        # initialize the threshold, a bit arbitrarily
        self.next_major_collection_threshold = (
            self.nursery_size * self.major_collection_threshold)
        debug_stop("gc-set-nursery-size")


    def malloc_fixedsize_clear(self, typeid, size, can_collect=True,
                               needs_finalizer=False, contains_weakptr=False):
        ll_assert(can_collect, "!can_collect")
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        rawtotalsize = llmemory.raw_malloc_usage(totalsize)
        #
        # If the object needs a finalizer, ask for a rawmalloc.
        # The following check should be constant-folded.
        if needs_finalizer:
            ll_assert(not contains_weakptr,
                     "'needs_finalizer' and 'contains_weakptr' both specified")
            result = self.malloc_with_finalizer(typeid, totalsize)
        #
        # If totalsize is greater than small_request_threshold, ask for
        # a rawmalloc.  The following check should be constant-folded.
        elif rawtotalsize > self.small_request_threshold:
            ll_assert(not contains_weakptr,
                      "'contains_weakptr' specified for a large object")
            result = self._external_malloc(typeid, totalsize)
            #
        else:
            # If totalsize is smaller than minimal_size_in_nursery, round it
            # up.  The following check should also be constant-folded.
            min_size = llmemory.raw_malloc_usage(self.minimal_size_in_nursery)
            if rawtotalsize < min_size:
                totalsize = rawtotalsize = min_size
            #
            # Get the memory from the nursery.  If there is not enough space
            # there, do a collect first.
            result = self.nursery_free
            self.nursery_free = result + totalsize
            if self.nursery_free > self.nursery_top:
                result = self.collect_and_reserve(totalsize)
            #
            # Build the object.
            llarena.arena_reserve(result, totalsize)
            self.init_gc_object(result, typeid, flags=0)
            #
            # If it is a weakref, record it (check constant-folded).
            if contains_weakptr:
                self.young_objects_with_weakrefs.append(result+size_gc_header)
        #
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)


    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length, can_collect):
        ll_assert(can_collect, "!can_collect")
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size
        try:
            varsize = ovfcheck(itemsize * length)
            totalsize = ovfcheck(nonvarsize + varsize)
        except OverflowError:
            raise MemoryError
        #
        # If totalsize is greater than small_request_threshold, ask for
        # a rawmalloc.
        if llmemory.raw_malloc_usage(totalsize) > self.small_request_threshold:
            result = self._external_malloc(typeid, totalsize)
            #
        else:
            # Round the size up to the next multiple of WORD.  Note that
            # this is done only if totalsize <= self.small_request_threshold,
            # i.e. it cannot overflow, and it keeps the property that
            # totalsize <= self.small_request_threshold.
            totalsize = llarena.round_up_for_allocation(totalsize)
            ll_assert(llmemory.raw_malloc_usage(totalsize) <=
                      self.small_request_threshold,
                      "round_up_for_allocation() rounded up too much?")
            #
            # 'totalsize' should contain at least the GC header and
            # the length word, so it should never be smaller than
            # 'minimal_size_in_nursery'
            ll_assert(llmemory.raw_malloc_usage(totalsize) >=
                      llmemory.raw_malloc_usage(self.minimal_size_in_nursery),
                      "malloc_varsize_clear(): totalsize < minimalsize")
            #
            # Get the memory from the nursery.  If there is not enough space
            # there, do a collect first.
            result = self.nursery_free
            self.nursery_free = result + totalsize
            if self.nursery_free > self.nursery_top:
                result = self.collect_and_reserve(totalsize)
            #
            # Build the object.
            llarena.arena_reserve(result, totalsize)
            self.init_gc_object(result, typeid, flags=0)
        #
        # Set the length and return the object.
        (result + size_gc_header + offset_to_length).signed[0] = length
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)


    def collect(self, gen=1):
        """Do a minor (gen=0) or major (gen>0) collection."""
        self.minor_collection()
        if gen > 0:
            self.major_collection()

    def collect_and_reserve(self, totalsize):
        """To call when nursery_free overflows nursery_top.
        Do a minor collection, and possibly also a major collection,
        and finally reserve 'totalsize' bytes at the start of the
        now-empty nursery.
        """
        self.minor_collection()
        #
        if self.get_total_memory_used() > self.next_major_collection_threshold:
            self.major_collection()
            #
            # The nursery might not be empty now, because of
            # execute_finalizers().  If it is almost full again,
            # we need to fix it with another call to minor_collection().
            if self.nursery_free + totalsize > self.nursery_top:
                self.minor_collection()
        #
        result = self.nursery_free
        self.nursery_free = result + totalsize
        ll_assert(self.nursery_free <= self.nursery_top, "nursery overflow")
        return result
    collect_and_reserve._dont_inline_ = True


    def _full_collect_if_needed(self, reserving_size):
        if (float(self.get_total_memory_used()) + reserving_size >
                self.next_major_collection_threshold):
            self.minor_collection()
            self.major_collection(reserving_size)

    def _reserve_external_memory(self, totalsize):
        """Do a raw_malloc() to get some external memory.
        Note that the returned memory is not cleared."""
        #
        result = llmemory.raw_malloc(totalsize)
        if not result:
            raise MemoryError("cannot allocate large object")
        #
        size_gc_header = self.gcheaderbuilder.size_gc_header
        self.rawmalloced_total_size += llmemory.raw_malloc_usage(totalsize)
        self.rawmalloced_objects.append(result + size_gc_header)
        return result

    def _external_malloc(self, typeid, totalsize):
        """Allocate a large object using raw_malloc()."""
        #
        # If somebody calls _external_malloc() a lot, we must eventually
        # force a full collection.
        self._full_collect_if_needed(totalsize)
        #
        result = self._reserve_external_memory(totalsize)
        llmemory.raw_memclear(result, totalsize)
        self.init_gc_object(result, typeid, GCFLAG_NO_YOUNG_PTRS)
        return result
    _external_malloc._dont_inline_ = True


    def _malloc_nonmovable(self, typeid, totalsize):
        """Allocate an object non-movable."""
        #
        # If somebody calls _malloc_nonmovable() a lot, we must eventually
        # force a full collection.
        self._full_collect_if_needed(totalsize)
        #
        rawtotalsize = llmemory.raw_malloc_usage(totalsize)
        if rawtotalsize <= self.small_request_threshold:
            #
            # Ask the ArenaCollection to do the malloc.
            totalsize = llarena.round_up_for_allocation(totalsize)
            result = self.ac.malloc(totalsize)
            #
        else:
            # The size asked for is too large for the ArenaCollection.
            result = self._reserve_external_memory(totalsize)
        #
        llmemory.raw_memclear(result, totalsize)
        self.init_gc_object(result, typeid, GCFLAG_NO_YOUNG_PTRS)
        return result


    def malloc_with_finalizer(self, typeid, totalsize):
        """Allocate an object with a finalizer."""
        #
        result = self._malloc_nonmovable(typeid, totalsize)
        size_gc_header = self.gcheaderbuilder.size_gc_header
        self.objects_with_finalizers.append(result + size_gc_header)
        return result
    malloc_with_finalizer._dont_inline_ = True


    # ----------
    # Other functions in the GC API

    def set_max_heap_size(self, size):
        self.max_heap_size = float(size)
        if self.max_heap_size > 0.0:
            if self.max_heap_size < self.next_major_collection_threshold:
                self.next_major_collection_threshold = self.max_heap_size

    def can_malloc_nonmovable(self):
        return True

    def can_move(self, obj):
        """Overrides the parent can_move()."""
        return self.is_in_nursery(obj)


    def shrink_array(self, obj, smallerlength):
        #
        # Only objects in the nursery can be "resized".  Resizing them
        # means recording that they have a smaller size, so that when
        # moved out of the nursery, they will consume less memory.
        if not self.is_in_nursery(obj):
            return False
        #
        size_gc_header = self.gcheaderbuilder.size_gc_header
        typeid = self.get_type_id(obj)
        totalsmallersize = (
            size_gc_header + self.fixed_size(typeid) +
            self.varsize_item_sizes(typeid) * smallerlength)
        llarena.arena_shrink_obj(obj - size_gc_header, totalsmallersize)
        #
        offset_to_length = self.varsize_offset_to_length(typeid)
        (obj + offset_to_length).signed[0] = smallerlength
        return True


    def malloc_fixedsize_nonmovable(self, typeid):
        """NOT_RPYTHON: not tested translated"""
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + self.fixed_size(typeid)
        #
        result = self._malloc_nonmovable(typeid, totalsize)
        obj = result + size_gc_header
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

    def malloc_varsize_nonmovable(self, typeid, length):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + self.fixed_size(typeid)
        itemsize = self.varsize_item_sizes(typeid)
        offset_to_length = self.varsize_offset_to_length(typeid)
        try:
            varsize = ovfcheck(itemsize * length)
            totalsize = ovfcheck(nonvarsize + varsize)
        except OverflowError:
            raise MemoryError
        #
        result = self._malloc_nonmovable(typeid, totalsize)
        obj = result + size_gc_header
        (obj + offset_to_length).signed[0] = length
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

    def malloc_nonmovable(self, typeid, length, zero):
        # helper for testing, same as GCBase.malloc
        if self.is_varsize(typeid):
            gcref = self.malloc_varsize_nonmovable(typeid, length)
        else:
            gcref = self.malloc_fixedsize_nonmovable(typeid)
        return gcref


    # ----------
    # Simple helpers

    def get_type_id(self, obj):
        tid = self.header(obj).tid
        return llop.extract_ushort(llgroup.HALFWORD, tid)

    def combine(self, typeid16, flags):
        return llop.combine_ushort(lltype.Signed, typeid16, flags)

    def init_gc_object(self, addr, typeid16, flags=0):
        # The default 'flags' is zero.  The flags GCFLAG_NO_xxx_PTRS
        # have been chosen to allow 'flags' to be zero in the common
        # case (hence the 'NO' in their name).
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = self.combine(typeid16, flags)

    def init_gc_object_immortal(self, addr, typeid16, flags=0):
        # For prebuilt GC objects, the flags must contain
        # GCFLAG_NO_xxx_PTRS, at least initially.
        flags |= GCFLAG_NO_HEAP_PTRS | GCFLAG_NO_YOUNG_PTRS
        self.init_gc_object(addr, typeid16, flags)

    def is_in_nursery(self, addr):
        ll_assert(llmemory.cast_adr_to_int(addr) & 1 == 0,
                  "odd-valued (i.e. tagged) pointer unexpected here")
        return self.nursery <= addr < self.nursery_top

    def is_forwarded(self, obj):
        """Returns True if the nursery obj is marked as forwarded.
        Implemented a bit obscurely by checking an unrelated flag
        that can never be set on a young object -- except if tid == -1.
        """
        assert self.is_in_nursery(obj)
        return self.header(obj).tid & GCFLAG_FINALIZATION_ORDERING

    def get_forwarding_address(self, obj):
        return llmemory.cast_adr_to_ptr(obj, FORWARDSTUBPTR).forw

    def get_total_memory_used(self):
        """Return the total memory used, not counting any object in the
        nursery: only objects in the ArenaCollection or raw-malloced.
        """
        return self.ac.total_memory_used + self.rawmalloced_total_size

    def debug_check_object(self, obj):
        # after a minor or major collection, no object should be in the nursery
        ll_assert(not self.is_in_nursery(obj),
                  "object in nursery after collection")
        # similarily, all objects should have this flag:
        ll_assert(self.header(obj).tid & GCFLAG_NO_YOUNG_PTRS,
                  "missing GCFLAG_NO_YOUNG_PTRS")
        # if we have GCFLAG_NO_HEAP_PTRS, then we have GCFLAG_NO_YOUNG_PTRS
        if self.header(obj).tid & GCFLAG_NO_HEAP_PTRS:
            ll_assert(self.header(obj).tid & GCFLAG_NO_YOUNG_PTRS,
                      "GCFLAG_NO_HEAP_PTRS && !GCFLAG_NO_YOUNG_PTRS")
        # the GCFLAG_VISITED should not be set between collections
        ll_assert(self.header(obj).tid & GCFLAG_VISITED == 0,
                  "unexpected GCFLAG_VISITED")
        # the GCFLAG_FINALIZATION_ORDERING should not be set between coll.
        ll_assert(self.header(obj).tid & GCFLAG_FINALIZATION_ORDERING == 0,
                  "unexpected GCFLAG_FINALIZATION_ORDERING")

    # ----------
    # Write barrier

    # for the JIT: a minimal description of the write_barrier() method
    # (the JIT assumes it is of the shape
    #  "if addr_struct.int0 & JIT_WB_IF_FLAG: remember_young_pointer()")
    JIT_WB_IF_FLAG = GCFLAG_NO_YOUNG_PTRS

    def write_barrier(self, newvalue, addr_struct):
        if self.header(addr_struct).tid & GCFLAG_NO_YOUNG_PTRS:
            self.remember_young_pointer(addr_struct, newvalue)

    def _init_writebarrier_logic(self):
        # The purpose of attaching remember_young_pointer to the instance
        # instead of keeping it as a regular method is to help the JIT call it.
        # Additionally, it makes the code in write_barrier() marginally smaller
        # (which is important because it is inlined *everywhere*).
        # For x86, there is also an extra requirement: when the JIT calls
        # remember_young_pointer(), it assumes that it will not touch the SSE
        # registers, so it does not save and restore them (that's a *hack*!).
        def remember_young_pointer(addr_struct, addr):
            # 'addr_struct' is the address of the object in which we write;
            # 'addr' is the address that we write in 'addr_struct'.
            ll_assert(not self.is_in_nursery(addr_struct),
                      "nursery object with GCFLAG_NO_YOUNG_PTRS")
            # if we have tagged pointers around, we first need to check whether
            # we have valid pointer here, otherwise we can do it after the
            # is_in_nursery check
            if (self.config.taggedpointers and
                not self.is_valid_gc_object(addr)):
                return
            #
            # Core logic: if the 'addr' is in the nursery, then we need
            # to remove the flag GCFLAG_NO_YOUNG_PTRS and add the old object
            # to the list 'old_objects_pointing_to_young'.  We know that
            # 'addr_struct' cannot be in the nursery, because nursery objects
            # never have the flag GCFLAG_NO_YOUNG_PTRS to start with.
            objhdr = self.header(addr_struct)
            if self.is_in_nursery(addr):
                self.old_objects_pointing_to_young.append(addr_struct)
                objhdr.tid &= ~GCFLAG_NO_YOUNG_PTRS
            elif (not self.config.taggedpointers and
                  not self.is_valid_gc_object(addr)):
                return
            #
            # Second part: if 'addr_struct' is actually a prebuilt GC
            # object and it's the first time we see a write to it, we
            # add it to the list 'prebuilt_root_objects'.  Note that we
            # do it even in the (rare?) case of 'addr' being another
            # prebuilt object, to simplify code.
            if objhdr.tid & GCFLAG_NO_HEAP_PTRS:
                objhdr.tid &= ~GCFLAG_NO_HEAP_PTRS
                self.prebuilt_root_objects.append(addr_struct)

        remember_young_pointer._dont_inline_ = True
        self.remember_young_pointer = remember_young_pointer


    def assume_young_pointers(self, addr_struct):
        """Called occasionally by the JIT to mean ``assume that 'addr_struct'
        may now contain young pointers.''
        """
        objhdr = self.header(addr_struct)
        if objhdr.tid & GCFLAG_NO_YOUNG_PTRS:
            self.old_objects_pointing_to_young.append(addr_struct)
            objhdr.tid &= ~GCFLAG_NO_YOUNG_PTRS
            #
            if objhdr.tid & GCFLAG_NO_HEAP_PTRS:
                objhdr.tid &= ~GCFLAG_NO_HEAP_PTRS
                self.prebuilt_root_objects.append(addr_struct)

    def writebarrier_before_copy(self, source_addr, dest_addr):
        """ This has the same effect as calling writebarrier over
        each element in dest copied from source, except it might reset
        one of the following flags a bit too eagerly, which means we'll have
        a bit more objects to track, but being on the safe side.
        """
        source_hdr = self.header(source_addr)
        dest_hdr = self.header(dest_addr)
        if dest_hdr.tid & GCFLAG_NO_YOUNG_PTRS == 0:
            return True
        # ^^^ a fast path of write-barrier
        #
        if source_hdr.tid & GCFLAG_NO_YOUNG_PTRS == 0:
            # there might be an object in source that is in nursery
            self.old_objects_pointing_to_young.append(dest_addr)
            dest_hdr.tid &= ~GCFLAG_NO_YOUNG_PTRS
        #
        if dest_hdr.tid & GCFLAG_NO_HEAP_PTRS:
            if source_hdr.tid & GCFLAG_NO_HEAP_PTRS == 0:
                dest_hdr.tid &= ~GCFLAG_NO_HEAP_PTRS
                self.prebuilt_root_objects.append(dest_addr)
        return True


    # ----------
    # Nursery collection

    def minor_collection(self):
        """Perform a minor collection: find the objects from the nursery
        that remain alive and move them out."""
        #
        debug_start("gc-minor")
        #
        # First, find the roots that point to nursery objects.  These
        # nursery objects are copied out of the nursery.  Note that
        # references to further nursery objects are not modified by
        # this step; only objects directly referenced by roots are
        # copied out.  They are also added to the list
        # 'old_objects_pointing_to_young'.
        self.collect_roots_in_nursery()
        #
        # Now trace objects from 'old_objects_pointing_to_young'.
        # All nursery objects they reference are copied out of the
        # nursery, and again added to 'old_objects_pointing_to_young'.
        # We proceed until 'old_objects_pointing_to_young' is empty.
        self.collect_oldrefs_to_nursery()
        #
        # Now all live nursery objects should be out.  Update the
        # young weakrefs' targets.
        if self.young_objects_with_weakrefs.length() > 0:
            self.invalidate_young_weakrefs()
        #
        # Clear this mapping.
        if self.young_objects_shadows.length() > 0:
            self.young_objects_shadows.clear()
        #
        # All live nursery objects are out, and the rest dies.  Fill
        # the whole nursery with zero and reset the current nursery pointer.
        llarena.arena_reset(self.nursery, self.nursery_size, 2)
        self.nursery_free = self.nursery
        #
        debug_print("minor collect, total memory used:",
                    self.get_total_memory_used())
        debug_stop("gc-minor")
        if 0:  # not we_are_translated():
            self.debug_check_consistency()     # xxx expensive!


    def collect_roots_in_nursery(self):
        # we don't need to trace prebuilt GcStructs during a minor collect:
        # if a prebuilt GcStruct contains a pointer to a young object,
        # then the write_barrier must have ensured that the prebuilt
        # GcStruct is in the list self.old_objects_pointing_to_young.
        self.root_walker.walk_roots(
            MiniMarkGC._trace_drag_out1,  # stack roots
            MiniMarkGC._trace_drag_out1,  # static in prebuilt non-gc
            None)                         # static in prebuilt gc

    def collect_oldrefs_to_nursery(self):
        # Follow the old_objects_pointing_to_young list and move the
        # young objects they point to out of the nursery.
        oldlist = self.old_objects_pointing_to_young
        while oldlist.non_empty():
            obj = oldlist.pop()
            #
            # Add the flag GCFLAG_NO_YOUNG_PTRS.  All live objects should have
            # this flag after a nursery collection.
            self.header(obj).tid |= GCFLAG_NO_YOUNG_PTRS
            #
            # Trace the 'obj' to replace pointers to nursery with pointers
            # outside the nursery, possibly forcing nursery objects out
            # and adding them to 'old_objects_pointing_to_young' as well.
            self.trace_and_drag_out_of_nursery(obj)

    def trace_and_drag_out_of_nursery(self, obj):
        """obj must not be in the nursery.  This copies all the
        young objects it references out of the nursery.
        """
        self.trace(obj, self._trace_drag_out, None)


    def _trace_drag_out1(self, root):
        self._trace_drag_out(root, None)

    def _trace_drag_out(self, root, ignored):
        obj = root.address[0]
        #
        # If 'obj' is not in the nursery, nothing to change.
        if not self.is_in_nursery(obj):
            return
        #
        # If 'obj' was already forwarded, change it to its forwarding address.
        if self.is_forwarded(obj):
            root.address[0] = self.get_forwarding_address(obj)
            return
        #
        # First visit to 'obj': we must move it out of the nursery.
        size_gc_header = self.gcheaderbuilder.size_gc_header
        size = self.get_size(obj)
        totalsize = size_gc_header + size
        #
        if self.header(obj).tid & GCFLAG_HAS_SHADOW == 0:
            #
            # Common case: allocate a new nonmovable location for it.
            newhdr = self.ac.malloc(totalsize)
            #
        else:
            # The object has already a shadow.
            newobj = self.young_objects_shadows.get(obj)
            ll_assert(newobj != NULL, "GCFLAG_HAS_SHADOW but no shadow found")
            newhdr = newobj - size_gc_header
            #
            # Remove the flag GCFLAG_HAS_SHADOW, so that it doesn't get
            # copied to the shadow itself.
            self.header(obj).tid &= ~GCFLAG_HAS_SHADOW
        #
        # Copy it.  Note that references to other objects in the
        # nursery are kept unchanged in this step.
        llmemory.raw_memcopy(obj - size_gc_header, newhdr, totalsize)
        #
        # Set the old object's tid to -1 (containing all flags) and
        # replace the old object's content with the target address.
        # A bit of no-ops to convince llarena that we are changing
        # the layout, in non-translated versions.
        obj = llarena.getfakearenaaddress(obj)
        llarena.arena_reset(obj - size_gc_header, totalsize, 0)
        llarena.arena_reserve(obj - size_gc_header,
                              size_gc_header + llmemory.sizeof(FORWARDSTUB))
        self.header(obj).tid = -1
        newobj = newhdr + size_gc_header
        llmemory.cast_adr_to_ptr(obj, FORWARDSTUBPTR).forw = newobj
        #
        # Change the original pointer to this object.
        root.address[0] = newobj
        #
        # Add the newobj to the list 'old_objects_pointing_to_young',
        # because it can contain further pointers to other young objects.
        # We will fix such references to point to the copy of the young
        # objects when we walk 'old_objects_pointing_to_young'.
        self.old_objects_pointing_to_young.append(newobj)


    # ----------
    # Full collection

    def major_collection(self, reserving_size=0):
        """Do a major collection.  Only for when the nursery is empty."""
        #
        debug_start("gc-collect")
        debug_print()
        debug_print(".----------- Full collection ------------------")
        debug_print("| used before collection:")
        debug_print("|          in ArenaCollection:     ",
                    self.ac.total_memory_used, "bytes")
        debug_print("|          raw_malloced:           ",
                    self.rawmalloced_total_size, "bytes")
        #
        # Debugging checks
        ll_assert(self.nursery_free == self.nursery,
                  "nursery not empty in major_collection()")
        self.debug_check_consistency()
        #
        # Note that a major collection is non-moving.  The goal is only to
        # find and free some of the objects allocated by the ArenaCollection.
        # We first visit all objects and toggle the flag GCFLAG_VISITED on
        # them, starting from the roots.
        self.objects_to_trace = self.AddressStack()
        self.collect_roots()
        self.visit_all_objects()
        #
        # Finalizer support: adds the flag GCFLAG_VISITED to all objects
        # with a finalizer and all objects reachable from there (and also
        # moves some objects from 'objects_with_finalizers' to
        # 'run_finalizers').
        if self.objects_with_finalizers.non_empty():
            self.deal_with_objects_with_finalizers()
        #
        self.objects_to_trace.delete()
        #
        # Weakref support: clear the weak pointers to dying objects
        if self.old_objects_with_weakrefs.non_empty():
            self.invalidate_old_weakrefs()
        #
        # Walk all rawmalloced objects and free the ones that don't
        # have the GCFLAG_VISITED flag.
        self.free_unvisited_rawmalloc_objects()
        #
        # Ask the ArenaCollection to visit all objects.  Free the ones
        # that have not been visited above, and reset GCFLAG_VISITED on
        # the others.
        self.ac.mass_free(self._free_if_unvisited)
        #
        # We also need to reset the GCFLAG_VISITED on prebuilt GC objects.
        self.prebuilt_root_objects.foreach(self._reset_gcflag_visited, None)
        #
        self.debug_check_consistency()
        #
        self.num_major_collects += 1
        debug_print("| used after collection:")
        debug_print("|          in ArenaCollection:     ",
                    self.ac.total_memory_used, "bytes")
        debug_print("|          raw_malloced:           ",
                    self.rawmalloced_total_size, "bytes")
        debug_print("| number of major collects:        ",
                    self.num_major_collects)
        debug_print("`----------------------------------------------")
        debug_stop("gc-collect")
        #
        # Set the threshold for the next major collection to be when we
        # have allocated 'major_collection_threshold' times more than
        # we currently have.
        self.next_major_collection_threshold = (
            (self.get_total_memory_used() * self.major_collection_threshold)
            + reserving_size)
        #
        # Max heap size: gives an upper bound on the threshold.  If we
        # already have at least this much allocated, raise MemoryError.
        if (self.max_heap_size > 0.0 and
                self.next_major_collection_threshold > self.max_heap_size):
            #
            self.next_major_collection_threshold = self.max_heap_size
            if (float(self.get_total_memory_used()) + reserving_size >=
                    self.next_major_collection_threshold):
                #
                # First raise MemoryError, giving the program a chance to
                # quit cleanly.  It might still allocate in the nursery,
                # which might eventually be emptied, triggering another
                # major collect and (possibly) reaching here again with an
                # even higher memory consumption.  To prevent it, if it's
                # the second time we are here, then abort the program.
                if self.max_heap_size_already_raised:
                    llop.debug_fatalerror(lltype.Void,
                                          "Using too much memory, aborting")
                self.max_heap_size_already_raised = True
                raise MemoryError
        #
        # At the end, we can execute the finalizers of the objects
        # listed in 'run_finalizers'.  Note that this will typically do
        # more allocations.
        self.execute_finalizers()


    def _free_if_unvisited(self, hdr):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        obj = hdr + size_gc_header
        if self.header(obj).tid & GCFLAG_VISITED:
            self.header(obj).tid &= ~GCFLAG_VISITED
            return False     # survives
        else:
            return True      # dies

    def _reset_gcflag_visited(self, obj, ignored):
        self.header(obj).tid &= ~GCFLAG_VISITED

    def free_unvisited_rawmalloc_objects(self):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        list = self.rawmalloced_objects
        self.rawmalloced_objects = self.AddressStack()
        #
        while list.non_empty():
            obj = list.pop()
            if self.header(obj).tid & GCFLAG_VISITED:
                self.header(obj).tid &= ~GCFLAG_VISITED   # survives
                self.rawmalloced_objects.append(obj)
            else:
                totalsize = size_gc_header + self.get_size(obj)
                rawtotalsize = llmemory.raw_malloc_usage(totalsize)
                self.rawmalloced_total_size -= rawtotalsize
                llmemory.raw_free(obj - size_gc_header)
        #
        list.delete()


    def collect_roots(self):
        # Collect all roots.  Starts from all the objects
        # from 'prebuilt_root_objects'.
        self.prebuilt_root_objects.foreach(self._collect_obj,
                                           self.objects_to_trace)
        #
        # Add the roots from the other sources.
        self.root_walker.walk_roots(
            MiniMarkGC._collect_ref,  # stack roots
            MiniMarkGC._collect_ref,  # static in prebuilt non-gc structures
            None)   # we don't need the static in all prebuilt gc objects
        #
        # If we are in an inner collection caused by a call to a finalizer,
        # the 'run_finalizers' objects also need to kept alive.
        self.run_finalizers.foreach(self._collect_obj,
                                    self.objects_to_trace)

    @staticmethod
    def _collect_obj(obj, objects_to_trace):
        objects_to_trace.append(obj)

    def _collect_ref(self, root):
        self.objects_to_trace.append(root.address[0])

    def _collect_ref_rec(self, root, ignored):
        self.objects_to_trace.append(root.address[0])

    def visit_all_objects(self):
        pending = self.objects_to_trace
        while pending.non_empty():
            obj = pending.pop()
            self.visit(obj)

    def visit(self, obj):
        #
        # 'obj' is a live object.  Check GCFLAG_VISITED to know if we
        # have already seen it before.
        #
        # Moreover, we can ignore prebuilt objects with GCFLAG_NO_HEAP_PTRS.
        # If they have this flag set, then they cannot point to heap
        # objects, so ignoring them is fine.  If they don't have this
        # flag set, then the object should be in 'prebuilt_root_objects',
        # and the GCFLAG_VISITED will be reset at the end of the
        # collection.
        hdr = self.header(obj)
        if hdr.tid & (GCFLAG_VISITED | GCFLAG_NO_HEAP_PTRS):
            return
        #
        # It's the first time.  We set the flag.
        hdr.tid |= GCFLAG_VISITED
        #
        # Trace the content of the object and put all objects it references
        # into the 'objects_to_trace' list.
        self.trace(obj, self._collect_ref_rec, None)


    # ----------
    # id() and identityhash() support

    def id_or_identityhash(self, gcobj, special_case_prebuilt):
        """Implement the common logic of id() and identityhash()
        of an object, given as a GCREF.
        """
        obj = llmemory.cast_ptr_to_adr(gcobj)
        #
        if self.is_valid_gc_object(obj):
            if self.is_in_nursery(obj):
                #
                # The object not a tagged pointer, and is it still in the
                # nursery.  Find or allocate a "shadow" object, which is
                # where the object will be moved by the next minor
                # collection
                if self.header(obj).tid & GCFLAG_HAS_SHADOW:
                    shadow = self.young_objects_shadows.get(obj)
                    ll_assert(shadow != NULL,
                              "GCFLAG_HAS_SHADOW but no shadow found")
                else:
                    size_gc_header = self.gcheaderbuilder.size_gc_header
                    size = self.get_size(obj)
                    shadowhdr = self.ac.malloc(size_gc_header + size)
                    # initialize to an invalid tid *without* GCFLAG_VISITED,
                    # so that if the object dies before the next minor
                    # collection, the shadow will stay around but be collected
                    # by the next major collection.
                    shadow = shadowhdr + size_gc_header
                    self.header(shadow).tid = 0
                    self.header(obj).tid |= GCFLAG_HAS_SHADOW
                    self.young_objects_shadows.setitem(obj, shadow)
                #
                # The answer is the address of the shadow.
                obj = shadow
                #
            elif special_case_prebuilt:
                if self.header(obj).tid & GCFLAG_HAS_SHADOW:
                    #
                    # For identityhash(), we need a special case for some
                    # prebuilt objects: their hash must be the same before
                    # and after translation.  It is stored as an extra word
                    # after the object.  But we cannot use it for id()
                    # because the stored value might clash with a real one.
                    size = self.get_size(obj)
                    return (obj + size).signed[0]
        #
        return llmemory.cast_adr_to_int(obj)


    def id(self, gcobj):
        return self.id_or_identityhash(gcobj, False)

    def identityhash(self, gcobj):
        return self.id_or_identityhash(gcobj, True)


    # ----------
    # Finalizers

    def deal_with_objects_with_finalizers(self):
        # Walk over list of objects with finalizers.
        # If it is not surviving, add it to the list of to-be-called
        # finalizers and make it survive, to make the finalizer runnable.
        # We try to run the finalizers in a "reasonable" order, like
        # CPython does.  The details of this algorithm are in
        # pypy/doc/discussion/finalizer-order.txt.
        new_with_finalizer = self.AddressDeque()
        marked = self.AddressDeque()
        pending = self.AddressStack()
        self.tmpstack = self.AddressStack()
        while self.objects_with_finalizers.non_empty():
            x = self.objects_with_finalizers.popleft()
            ll_assert(self._finalization_state(x) != 1,
                      "bad finalization state 1")
            if self.header(x).tid & GCFLAG_VISITED:
                new_with_finalizer.append(x)
                continue
            marked.append(x)
            pending.append(x)
            while pending.non_empty():
                y = pending.pop()
                state = self._finalization_state(y)
                if state == 0:
                    self._bump_finalization_state_from_0_to_1(y)
                    self.trace(y, self._append_if_nonnull, pending)
                elif state == 2:
                    self._recursively_bump_finalization_state_from_2_to_3(y)
            self._recursively_bump_finalization_state_from_1_to_2(x)

        while marked.non_empty():
            x = marked.popleft()
            state = self._finalization_state(x)
            ll_assert(state >= 2, "unexpected finalization state < 2")
            if state == 2:
                self.run_finalizers.append(x)
                # we must also fix the state from 2 to 3 here, otherwise
                # we leave the GCFLAG_FINALIZATION_ORDERING bit behind
                # which will confuse the next collection
                self._recursively_bump_finalization_state_from_2_to_3(x)
            else:
                new_with_finalizer.append(x)

        self.tmpstack.delete()
        pending.delete()
        marked.delete()
        self.objects_with_finalizers.delete()
        self.objects_with_finalizers = new_with_finalizer

    def _append_if_nonnull(pointer, stack):
        stack.append(pointer.address[0])
    _append_if_nonnull = staticmethod(_append_if_nonnull)

    def _finalization_state(self, obj):
        tid = self.header(obj).tid
        if tid & GCFLAG_VISITED:
            if tid & GCFLAG_FINALIZATION_ORDERING:
                return 2
            else:
                return 3
        else:
            if tid & GCFLAG_FINALIZATION_ORDERING:
                return 1
            else:
                return 0

    def _bump_finalization_state_from_0_to_1(self, obj):
        ll_assert(self._finalization_state(obj) == 0,
                  "unexpected finalization state != 0")
        hdr = self.header(obj)
        hdr.tid |= GCFLAG_FINALIZATION_ORDERING

    def _recursively_bump_finalization_state_from_2_to_3(self, obj):
        ll_assert(self._finalization_state(obj) == 2,
                  "unexpected finalization state != 2")
        pending = self.tmpstack
        ll_assert(not pending.non_empty(), "tmpstack not empty")
        pending.append(obj)
        while pending.non_empty():
            y = pending.pop()
            hdr = self.header(y)
            if hdr.tid & GCFLAG_FINALIZATION_ORDERING:     # state 2 ?
                hdr.tid &= ~GCFLAG_FINALIZATION_ORDERING   # change to state 3
                self.trace(y, self._append_if_nonnull, pending)

    def _recursively_bump_finalization_state_from_1_to_2(self, obj):
        # recursively convert objects from state 1 to state 2.
        # The call to visit_all_objects() will add the GCFLAG_VISITED
        # recursively.
        self.objects_to_trace.append(obj)
        self.visit_all_objects()


    # ----------
    # Weakrefs

    # The code relies on the fact that no weakref can be an old object
    # weakly pointing to a young object.  Indeed, weakrefs are immutable
    # so they cannot point to an object that was created after it.
    def invalidate_young_weakrefs(self):
        """Called during a nursery collection."""
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
                    (obj + offset).address[0] = llmemory.NULL
                    continue    # no need to remember this weakref any longer
            self.old_objects_with_weakrefs.append(obj)


    def invalidate_old_weakrefs(self):
        """Called during a major collection."""
        # walk over list of objects that contain weakrefs
        # if the object it references does not survive, invalidate the weakref
        new_with_weakref = self.AddressStack()
        while self.old_objects_with_weakrefs.non_empty():
            obj = self.old_objects_with_weakrefs.pop()
            if self.header(obj).tid & GCFLAG_VISITED == 0:
                continue # weakref itself dies
            offset = self.weakpointer_offset(self.get_type_id(obj))
            pointing_to = (obj + offset).address[0]
            if self.header(pointing_to).tid & GCFLAG_VISITED:
                new_with_weakref.append(obj)
            else:
                (obj + offset).address[0] = llmemory.NULL
        self.old_objects_with_weakrefs.delete()
        self.old_objects_with_weakrefs = new_with_weakref


# ____________________________________________________________

# For testing, a simple implementation of ArenaCollection.
# This version could be used together with obmalloc.c, but
# it requires an extra word per object in the 'all_objects'
# list.

class SimpleArenaCollection(object):

    def __init__(self, arena_size, page_size, small_request_threshold):
        self.arena_size = arena_size   # ignored
        self.page_size = page_size
        self.small_request_threshold = small_request_threshold
        self.all_objects = []
        self.total_memory_used = 0

    def malloc(self, size):
        nsize = llmemory.raw_malloc_usage(size)
        ll_assert(nsize > 0, "malloc: size is null or negative")
        ll_assert(nsize <= self.small_request_threshold,"malloc: size too big")
        ll_assert((nsize & (WORD-1)) == 0, "malloc: size is not aligned")
        #
        result = llarena.arena_malloc(nsize, False)
        llarena.arena_reserve(result, size)
        self.all_objects.append((result, nsize))
        self.total_memory_used += nsize
        return result

    def mass_free(self, ok_to_free_func):
        objs = self.all_objects
        self.all_objects = []
        self.total_memory_used = 0
        for rawobj, nsize in objs:
            if ok_to_free_func(rawobj):
                llarena.arena_free(rawobj)
            else:
                self.all_objects.append((rawobj, nsize))
                self.total_memory_used += nsize
