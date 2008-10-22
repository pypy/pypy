from pypy.rpython.lltypesystem.llmemory import raw_malloc, raw_free
from pypy.rpython.lltypesystem.llmemory import raw_memcopy, raw_memclear
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rpython.memory.support import get_address_stack, get_address_deque
from pypy.rpython.memory.support import AddressDict
from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rlib.objectmodel import free_non_gc_object
from pypy.rlib.debug import ll_assert
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.memory.gc.base import MovingGCBase

import sys, os, time

TYPEID_MASK = 0xffff
first_gcflag = 1 << 16
GCFLAG_FORWARDED = first_gcflag
# GCFLAG_EXTERNAL is set on objects not living in the semispace:
# either immortal objects or (for HybridGC) externally raw_malloc'ed
GCFLAG_EXTERNAL = first_gcflag << 1
GCFLAG_FINALIZATION_ORDERING = first_gcflag << 2

memoryError = MemoryError()

class SemiSpaceGC(MovingGCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    malloc_zero_filled = True
    first_unused_gcflag = first_gcflag << 3
    total_collection_time = 0.0
    total_collection_count = 0

    HDR = lltype.Struct('header', ('tid', lltype.Signed))
    FORWARDSTUB = lltype.GcStruct('forwarding_stub',
                                  ('forw', llmemory.Address))
    FORWARDSTUBPTR = lltype.Ptr(FORWARDSTUB)

    # the following values override the default arguments of __init__ when
    # translating to a real backend.
    TRANSLATION_PARAMS = {'space_size': 8*1024*1024} # XXX adjust

    def __init__(self, config, chunk_size=DEFAULT_CHUNK_SIZE, space_size=4096,
                 max_space_size=sys.maxint//2+1):
        MovingGCBase.__init__(self, config, chunk_size)
        self.space_size = space_size
        self.max_space_size = max_space_size
        self.red_zone = 0

    def setup(self):
        if self.config.gcconfig.debugprint:
            self.program_start_time = time.time()
        self.tospace = llarena.arena_malloc(self.space_size, True)
        ll_assert(bool(self.tospace), "couldn't allocate tospace")
        self.top_of_space = self.tospace + self.space_size
        self.fromspace = llarena.arena_malloc(self.space_size, True)
        ll_assert(bool(self.fromspace), "couldn't allocate fromspace")
        self.free = self.tospace
        MovingGCBase.setup(self)
        self.objects_with_finalizers = self.AddressDeque()
        self.objects_with_weakrefs = self.AddressStack()

    # This class only defines the malloc_{fixed,var}size_clear() methods
    # because the spaces are filled with zeroes in advance.

    def malloc_fixedsize_clear(self, typeid, size, can_collect,
                               has_finalizer=False, contains_weakptr=False):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self.free
        if raw_malloc_usage(totalsize) > self.top_of_space - result:
            if not can_collect:
                raise memoryError
            result = self.obtain_free_space(totalsize)
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid)
        self.free = result + totalsize
        if has_finalizer:
            self.objects_with_finalizers.append(result + size_gc_header)
        if contains_weakptr:
            self.objects_with_weakrefs.append(result + size_gc_header)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length, can_collect,
                             has_finalizer=False):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size
        try:
            varsize = ovfcheck(itemsize * length)
            totalsize = ovfcheck(nonvarsize + varsize)
        except OverflowError:
            raise memoryError
        result = self.free
        if raw_malloc_usage(totalsize) > self.top_of_space - result:
            if not can_collect:
                raise memoryError
            result = self.obtain_free_space(totalsize)
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid)
        (result + size_gc_header + offset_to_length).signed[0] = length
        self.free = result + llarena.round_up_for_allocation(totalsize)
        if has_finalizer:
            self.objects_with_finalizers.append(result + size_gc_header)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    def obtain_free_space(self, needed):
        # a bit of tweaking to maximize the performance and minimize the
        # amount of code in an inlined version of malloc_fixedsize_clear()
        if not self.try_obtain_free_space(needed):
            raise memoryError
        return self.free
    obtain_free_space._dont_inline_ = True

    def try_obtain_free_space(self, needed):
        # XXX for bonus points do big objects differently
        needed = raw_malloc_usage(needed)
        if (self.red_zone >= 2 and self.space_size < self.max_space_size and
            self.double_space_size()):
            pass    # collect was done during double_space_size()
        else:
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
            ll_assert(needed <= self.top_of_space - self.free,
                         "double_space_size() failed to do its job")
            return True

    def double_space_size(self):
        self.red_zone = 0
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
            ll_assert(self.free <= self.top_of_space,
                         "unexpected growth of GC space usage during collect")
            return False     # out of memory

        self.fromspace = newspace
        self.space_size = newsize
        return True    # success

    def set_max_heap_size(self, size):
        # Set the maximum semispace size.  Note that the logic above will
        # round this number *up* to the next power of two.  Also, this is
        # the size of one semispace only, so actual usage can be the double
        # during a collection.  Finally, note that this will never shrink
        # an already-allocated heap.
        self.max_space_size = size

    def collect(self):
        self.debug_check_consistency()
        self.semispace_collect()
        # the indirection is required by the fact that collect() is referred
        # to by the gc transformer, and the default argument would crash
        # (this is also a hook for the HybridGC)

    def semispace_collect(self, size_changing=False):
        if self.config.gcconfig.debugprint:
            llop.debug_print(lltype.Void)
            llop.debug_print(lltype.Void,
                             ".----------- Full collection ------------------")
            start_usage = self.free - self.tospace
            llop.debug_print(lltype.Void,
                             "| used before collection:          ",
                             start_usage, "bytes")
            start_time = time.time()
        #llop.debug_print(lltype.Void, 'semispace_collect', int(size_changing))
        tospace = self.fromspace
        fromspace = self.tospace
        start_time = 0 # Help the flow space
        start_usage = 0 # Help the flow space
        self.fromspace = fromspace
        self.tospace = tospace
        self.top_of_space = tospace + self.space_size
        scan = self.free = tospace
        self.starting_full_collect()
        self.collect_roots()
        if self.run_finalizers.non_empty():
            self.update_run_finalizers()
        scan = self.scan_copied(scan)
        if self.objects_with_finalizers.non_empty():
            scan = self.deal_with_objects_with_finalizers(scan)
        if self.objects_with_weakrefs.non_empty():
            self.invalidate_weakrefs()
        self.update_objects_with_id()
        self.finished_full_collect()
        self.debug_check_consistency()
        if not size_changing:
            llarena.arena_reset(fromspace, self.space_size, True)
            self.record_red_zone()
            self.execute_finalizers()
        #llop.debug_print(lltype.Void, 'collected', self.space_size, size_changing, self.top_of_space - self.free)
        if self.config.gcconfig.debugprint:
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.total_collection_time += elapsed_time
            self.total_collection_count += 1
            total_program_time = end_time - self.program_start_time
            end_usage = self.free - self.tospace
            llop.debug_print(lltype.Void,
                             "| used after collection:           ",
                             end_usage, "bytes")
            llop.debug_print(lltype.Void,
                             "| freed:                           ",
                             start_usage - end_usage, "bytes")
            llop.debug_print(lltype.Void,
                             "| size of each semispace:          ",
                             self.space_size, "bytes")
            llop.debug_print(lltype.Void,
                             "| fraction of semispace now used:  ",
                             end_usage * 100.0 / self.space_size, "%")
            ct = self.total_collection_time
            cc = self.total_collection_count
            llop.debug_print(lltype.Void,
                             "| number of semispace_collects:    ",
                             cc)
            llop.debug_print(lltype.Void,
                             "|                         i.e.:    ",
                             cc / total_program_time, "per second")
            llop.debug_print(lltype.Void,
                             "| total time in semispace_collect: ",
                             ct, "seconds")
            llop.debug_print(lltype.Void,
                             "|                            i.e.: ",
                             ct * 100.0 / total_program_time, "%")
            llop.debug_print(lltype.Void,
                             "`----------------------------------------------")

    def starting_full_collect(self):
        pass    # hook for the HybridGC

    def finished_full_collect(self):
        pass    # hook for the HybridGC

    def record_red_zone(self):
        # red zone: if the space is more than 80% full, the next collection
        # should double its size.  If it is more than 66% full twice in a row,
        # then it should double its size too.  (XXX adjust)
        # The goal is to avoid many repeated collection that don't free a lot
        # of memory each, if the size of the live object set is just below the
        # size of the space.
        free_after_collection = self.top_of_space - self.free
        if free_after_collection > self.space_size // 3:
            self.red_zone = 0
        else:
            self.red_zone += 1
            if free_after_collection < self.space_size // 5:
                self.red_zone += 1

    def scan_copied(self, scan):
        while scan < self.free:
            curr = scan + self.size_gc_header()
            self.trace_and_copy(curr)
            scan += self.size_gc_header() + self.get_size(curr)
        return scan

    def collect_roots(self):
        self.root_walker.walk_roots(
            SemiSpaceGC._collect_root,  # stack roots
            SemiSpaceGC._collect_root,  # static in prebuilt non-gc structures
            SemiSpaceGC._collect_root)  # static in prebuilt gc objects

    def _collect_root(self, root):
        root.address[0] = self.copy(root.address[0])

    def copy(self, obj):
        if self.DEBUG:
            self.debug_check_can_copy(obj)
        if self.is_forwarded(obj):
            #llop.debug_print(lltype.Void, obj, "already copied to", self.get_forwarding_address(obj))
            return self.get_forwarding_address(obj)
        else:
            objsize = self.get_size(obj)
            newobj = self.make_a_copy(obj, objsize)
            #llop.debug_print(lltype.Void, obj, "copied to", newobj,
            #                 "tid", self.header(obj).tid,
            #                 "size", totalsize)
            self.set_forwarding_address(obj, newobj, objsize)
            return newobj

    def make_a_copy(self, obj, objsize):
        totalsize = self.size_gc_header() + objsize
        newaddr = self.free
        self.free += totalsize
        llarena.arena_reserve(newaddr, totalsize)
        raw_memcopy(obj - self.size_gc_header(), newaddr, totalsize)
        newobj = newaddr + self.size_gc_header()
        return newobj

    def trace_and_copy(self, obj):
        self.trace(obj, self._trace_copy, None)

    def _trace_copy(self, pointer, ignored):
        if pointer.address[0] != NULL:
            pointer.address[0] = self.copy(pointer.address[0])

    def surviving(self, obj):
        # To use during a collection.  Check if the object is currently
        # marked as surviving the collection.  This is equivalent to
        # self.is_forwarded() for all objects except the nonmoving objects
        # created by the HybridGC subclass.  In all cases, if an object
        # survives, self.get_forwarding_address() returns its new address.
        return self.is_forwarded(obj)

    def is_forwarded(self, obj):
        return self.header(obj).tid & GCFLAG_FORWARDED != 0
        # note: all prebuilt objects also have this flag set

    def get_forwarding_address(self, obj):
        tid = self.header(obj).tid
        if tid & GCFLAG_EXTERNAL:
            self.visit_external_object(obj)
            return obj      # external or prebuilt objects are "forwarded"
                            # to themselves
        else:
            stub = llmemory.cast_adr_to_ptr(obj, self.FORWARDSTUBPTR)
            return stub.forw

    def visit_external_object(self, obj):
        pass    # hook for the HybridGC

    def set_forwarding_address(self, obj, newobj, objsize):
        # To mark an object as forwarded, we set the GCFLAG_FORWARDED and
        # overwrite the object with a FORWARDSTUB.  Doing so is a bit
        # long-winded on llarena, but it all melts down to two memory
        # writes after translation to C.
        size_gc_header = self.size_gc_header()
        stubsize = llmemory.sizeof(self.FORWARDSTUB)
        tid = self.header(obj).tid
        ll_assert(tid & GCFLAG_EXTERNAL == 0,  "unexpected GCFLAG_EXTERNAL")
        ll_assert(tid & GCFLAG_FORWARDED == 0, "unexpected GCFLAG_FORWARDED")
        # replace the object at 'obj' with a FORWARDSTUB.
        hdraddr = obj - size_gc_header
        llarena.arena_reset(hdraddr, size_gc_header + objsize, False)
        llarena.arena_reserve(hdraddr, size_gc_header + stubsize)
        hdr = llmemory.cast_adr_to_ptr(hdraddr, lltype.Ptr(self.HDR))
        hdr.tid = tid | GCFLAG_FORWARDED
        stub = llmemory.cast_adr_to_ptr(obj, self.FORWARDSTUBPTR)
        stub.forw = newobj

    def get_type_id(self, addr):
        tid = self.header(addr).tid
        ll_assert(tid & (GCFLAG_FORWARDED|GCFLAG_EXTERNAL) != GCFLAG_FORWARDED,
                  "get_type_id on forwarded obj")
        # Non-prebuilt forwarded objects are overwritten with a FORWARDSTUB.
        # Although calling get_type_id() on a forwarded object works by itself,
        # we catch it as an error because it's likely that what is then
        # done with the typeid is bogus.
        return tid & TYPEID_MASK

    def init_gc_object(self, addr, typeid, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = typeid | flags

    def init_gc_object_immortal(self, addr, typeid, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = typeid | flags | GCFLAG_EXTERNAL | GCFLAG_FORWARDED
        # immortal objects always have GCFLAG_FORWARDED set;
        # see get_forwarding_address().

    def deal_with_objects_with_finalizers(self, scan):
        # walk over list of objects with finalizers
        # if it is not copied, add it to the list of to-be-called finalizers
        # and copy it, to me make the finalizer runnable
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
            if self.surviving(x):
                new_with_finalizer.append(self.get_forwarding_address(x))
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
            scan = self._recursively_bump_finalization_state_from_1_to_2(
                       x, scan)

        while marked.non_empty():
            x = marked.popleft()
            state = self._finalization_state(x)
            ll_assert(state >= 2, "unexpected finalization state < 2")
            newx = self.get_forwarding_address(x)
            if state == 2:
                self.run_finalizers.append(newx)
                # we must also fix the state from 2 to 3 here, otherwise
                # we leave the GCFLAG_FINALIZATION_ORDERING bit behind
                # which will confuse the next collection
                self._recursively_bump_finalization_state_from_2_to_3(x)
            else:
                new_with_finalizer.append(newx)

        self.tmpstack.delete()
        pending.delete()
        marked.delete()
        self.objects_with_finalizers.delete()
        self.objects_with_finalizers = new_with_finalizer
        return scan

    def _append_if_nonnull(pointer, stack):
        if pointer.address[0] != NULL:
            stack.append(pointer.address[0])
    _append_if_nonnull = staticmethod(_append_if_nonnull)

    def _finalization_state(self, obj):
        if self.surviving(obj):
            newobj = self.get_forwarding_address(obj)
            hdr = self.header(newobj)
            if hdr.tid & GCFLAG_FINALIZATION_ORDERING:
                return 2
            else:
                return 3
        else:
            hdr = self.header(obj)
            if hdr.tid & GCFLAG_FINALIZATION_ORDERING:
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
        newobj = self.get_forwarding_address(obj)
        pending = self.tmpstack
        ll_assert(not pending.non_empty(), "tmpstack not empty")
        pending.append(newobj)
        while pending.non_empty():
            y = pending.pop()
            hdr = self.header(y)
            if hdr.tid & GCFLAG_FINALIZATION_ORDERING:     # state 2 ?
                hdr.tid &= ~GCFLAG_FINALIZATION_ORDERING   # change to state 3
                self.trace(y, self._append_if_nonnull, pending)

    def _recursively_bump_finalization_state_from_1_to_2(self, obj, scan):
        # recursively convert objects from state 1 to state 2.
        # Note that copy() copies all bits, including the
        # GCFLAG_FINALIZATION_ORDERING.  The mapping between
        # state numbers and the presence of this bit was designed
        # for the following to work :-)
        self.copy(obj)
        return self.scan_copied(scan)

    def invalidate_weakrefs(self):
        # walk over list of objects that contain weakrefs
        # if the object it references survives then update the weakref
        # otherwise invalidate the weakref
        new_with_weakref = self.AddressStack()
        while self.objects_with_weakrefs.non_empty():
            obj = self.objects_with_weakrefs.pop()
            if not self.surviving(obj):
                continue # weakref itself dies
            obj = self.get_forwarding_address(obj)
            offset = self.weakpointer_offset(self.get_type_id(obj))
            pointing_to = (obj + offset).address[0]
            # XXX I think that pointing_to cannot be NULL here
            if pointing_to:
                if self.surviving(pointing_to):
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
        new_run_finalizer = self.AddressDeque()
        while self.run_finalizers.non_empty():
            obj = self.run_finalizers.popleft()
            new_run_finalizer.append(self.copy(obj))
        self.run_finalizers.delete()
        self.run_finalizers = new_run_finalizer

    def _is_external(self, obj):
        return (self.header(obj).tid & GCFLAG_EXTERNAL) != 0

    def debug_check_object(self, obj):
        """Check the invariants about 'obj' that should be true
        between collections."""
        tid = self.header(obj).tid
        if tid & GCFLAG_EXTERNAL:
            ll_assert(tid & GCFLAG_FORWARDED, "bug: external+!forwarded")
            ll_assert(not (self.tospace <= obj < self.free),
                      "external flag but object inside the semispaces")
        else:
            ll_assert(not (tid & GCFLAG_FORWARDED), "bug: !external+forwarded")
            ll_assert(self.tospace <= obj < self.free,
                      "!external flag but object outside the semispaces")
        ll_assert(not (tid & GCFLAG_FINALIZATION_ORDERING),
                  "unexpected GCFLAG_FINALIZATION_ORDERING")

    def debug_check_can_copy(self, obj):
        ll_assert(not (self.tospace <= obj < self.free),
                  "copy() on already-copied object")

    STATISTICS_NUMBERS = 0

