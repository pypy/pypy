from rpython.rtyper.lltypesystem import lltype, llmemory, llarena, rffi
from rpython.rlib.rarithmetic import LONG_BIT, r_uint
from rpython.rlib.objectmodel import free_non_gc_object, we_are_translated
from rpython.rlib.debug import ll_assert, fatalerror
from rpython.rlib.debug import debug_start, debug_stop, debug_print
from rpython.rlib import rthread, atomic_ops

WORD = LONG_BIT // 8
NULL = llmemory.NULL
WORD_POWER_2 = {32: 2, 64: 3}[LONG_BIT]
assert 1 << WORD_POWER_2 == WORD

# Linux's glibc is good at 'malloc(1023*WORD)': the blocks ("pages") it
# returns are exactly 1024 words apart, reserving only one extra word
# for its internal data.  Here we assume that even on other systems it
# will not use more than two words.
TRANSLATED_PAGE_SIZE = 1022 * WORD

# This is the largest size that StmGCSharedArea will map to its internal
# "pages" structures.
TRANSLATED_SMALL_REQUEST_THRESHOLD = 35 * WORD

# ------------------------------------------------------------
# The basic idea here is that each page will contain objects that are
# each of the same size.  Moreover each page belongs to one thread only:
# only this thread can use it to satisfy more allocations --- with however
# one exception: pages with low usage after a major collection are moved
# to a global list where any thread can pick them up.

PAGE_PTR = lltype.Ptr(lltype.ForwardReference())
PAGE_HEADER = lltype.Struct('PageHeader',
    # -- The following pointer makes a chained list of pages.
    ('nextpage', PAGE_PTR),
    # -- The following is only used when the page belongs to StmGCSharedArea.
    #    It makes another free list, used for various purposes.
    ('secondary_free_list', llmemory.Address),
    # -- The structure above is 2 words, which is a good value:
    #    '(1022-2) % N' is zero or very small for various small N's,
    #    i.e. there is not much wasted space.
    )
PAGE_PTR.TO.become(PAGE_HEADER)
PAGE_NULL = lltype.nullptr(PAGE_HEADER)

# ------------------------------------------------------------


class StmGCSharedArea(object):
    _alloc_flavor_ = 'raw'

    def __init__(self, gc, page_size, small_request_threshold):
        "NOT_RPYTHON"
        self.gc = gc
        self.page_size = page_size
        self.small_request_threshold = small_request_threshold
        #
        # This array contains 'length' chained lists of pages.
        # For each size N between WORD and 'small_request_threshold'
        # (included), the corresponding chained list contains pages
        # which store objects of size N.  This is only used for pages
        # with low usage after a major collection; as soon as a page
        # is used, or if its usage says high after a major collection,
        # it belongs to the lists of StmGCThreadLocalAllocator.
        length = small_request_threshold / WORD + 1
        self.low_usage_pages = lltype.malloc(rffi.CArray(PAGE_PTR), length,
                                             flavor='raw', zero=True,
                                             immortal=True)
        # ^^^ XXX not used so far
        self.full_pages = lltype.malloc(rffi.CArray(PAGE_PTR), length,
                                        flavor='raw', zero=True,
                                        immortal=True)
        self.nblocks_for_size = lltype.malloc(rffi.CArray(lltype.Signed),
                                              length, flavor='raw', zero=True,
                                              immortal=True)
        self.hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))
        for i in range(1, length):
            self.nblocks_for_size[i] = (page_size - self.hdrsize) // (WORD * i)
        assert self.nblocks_for_size[length-1] >= 1
        self.length = length
        #
        # Counters for statistics
        self.count_global_pages = 0
        self.num_major_collects = 0
        self.v_count_total_bytes = lltype.malloc(rffi.CArray(lltype.Unsigned),
                                                 1, flavor='raw',
                                                 immortal=True, zero=True)

    def setup(self):
        pass

    def fetch_count_total_bytes(self):
        return self.v_count_total_bytes[0]

    def fetch_count_total_bytes_and_add(self, increment):
        adr = rffi.cast(llmemory.Address, self.v_count_total_bytes)
        return r_uint(atomic_ops.fetch_and_add(adr, increment))

    def do_major_collection(self):
        """Perform a major collection."""
        # At this point all other threads should be blocked or running
        # external C code or careful non-GC-using code, with all GC roots
        # in their shadow stack.  Even if some nurseries are not empty
        # we can still trace through them: a major collection does not
        # move any object.  The point is only that after the "sweep" phase,
        # we have identified all locations that are now free, and added
        # them to the chained lists of StmGCSharedArea for reuse.
        debug_start("gc-collect")
        debug_print()
        debug_print(".----------- Full collection ------------------")
        debug_print("| used before collection:   ",
                    self.fetch_count_total_bytes(), "bytes")
        #
        # Note that a major collection is non-moving.  The goal is only to
        # find and free some of the objects allocated by the ArenaCollection.
        # We first visit all objects and set the flag GCFLAG_VISITED on them.
        self.objects_to_trace = self.AddressStack()
        #
        # The stacks...
        self.collect_roots_from_stacks()
        #
        # The raw structures...
        self.collect_from_raw_structures()
        #
        # The tldicts...
        self.collect_roots_from_tldicts()
        #
        self.visit_all_objects()
        #
        self.num_major_collects += 1
        debug_print("| used after collection:    ",
                    self.fetch_count_total_bytes(), "bytes")
        debug_print("| number of major collects: ",
                    self.num_major_collects)
        debug_print("`----------------------------------------------")
        debug_stop("gc-collect")

    def collect_roots_from_stacks(self):
        self.gc.root_walker.walk_all_stack_roots(StmGCSharedArea._collect_stack_root,
                                                 self)

    def collect_from_raw_structures(self):
        self.gc.root_walker.walk_current_nongc_roots(
            StmGCSharedArea._collect_stack_root, self)

    def _collect_stack_root(self, root):
        self.objects_to_trace.append(root.address[0])

    def collect_roots_from_tldicts(self):
        CALLBACK = self.gc.stm_operations.CALLBACK_ENUM
        llop.nop(lltype.Void, llhelper(CALLBACK,
                                       StmGCSharedArea._stm_enum_external_callback))
        # The previous line causes the _stm_enum_external_callback() function to be
        # generated in the C source with a specific signature, where it
        # can be called by the C code.
        stmtls = self.gc.linked_list_stmtls
        while stmtls is not None:
            self.visit_all_objects()   # empty the list first
            # for every stmtls:
            self.gc.stm_operations.tldict_enum_external(stmtls.thread_descriptor)
            stmtls = stmtls.linked_list_next

    @staticmethod
    def _stm_enum_external_callback(globalobj, localobj):
        localhdr = self.gc.header(localobj)
        ll_assert(localhdr.tid & GCFLAG_VISITED != 0,
                  "[shared] in a root: missing GCFLAG_VISITED")
        localhdr.tid &= ~GCFLAG_VISITED
        self.objects_to_trace.append(localobj)
        self.objects_to_trace.append(globalobj)

    def visit_all_objects(self):
        pending = self.objects_to_trace
        while pending.non_empty():
            obj = pending.pop()
            self.visit(obj)

    def visit(self, obj):
        # 'obj' is a live object.  Check GCFLAG_VISITED to know if we
        # have already seen it before.
        hdr = self.gc.header(obj)
        if hdr.tid & GCFLAG_VISITED:
            return
        #
        # It's the first time.  We set the flag.
        hdr.tid |= GCFLAG_VISITED
        #
        # Trace the content of the object and put all objects it references
        # into the 'objects_to_trace' list.
        self.gc.trace(obj, self._collect_ref_rec, None)

    def _collect_ref_rec(self, root, ignored):
        self.objects_to_trace.append(root.address[0])


# ------------------------------------------------------------


class StmGCThreadLocalAllocator(object):
    """A thread-local allocator for the shared area.
    This is an optimization only: it lets us use thread-local variables
    to keep track of what we allocated.
    """
    _alloc_flavor_ = 'raw'

    def __init__(self, sharedarea):
        self.gc = sharedarea.gc
        self.sharedarea = sharedarea
        #
        # The array 'pages_for_size' contains 'length' chained lists
        # of pages currently managed by this thread.
        # For each size N between WORD and 'small_request_threshold'
        # (included), the corresponding chained list contains pages
        # which store objects of size N.
        length = sharedarea.length
        self.pages_for_size = lltype.malloc(
            rffi.CArray(PAGE_PTR), length, flavor='raw', zero=True,
            track_allocation=False)
        self.count_pages = 0    # for statistics
        #
        # This array contains 'length' chained lists of free locations.
        self.free_loc_for_size = lltype.malloc(
            rffi.CArray(llmemory.Address), length, flavor='raw', zero=True,
            track_allocation=False)
        #
        if not we_are_translated():
            self._seen_pages = set()

    def _malloc_size_class(self, size_class):
        """Malloc one object of the given size_class (== number of WORDs)."""
        ll_assert(size_class > 0, "malloc_size_class: null or neg size_class")
        ll_assert(size_class <= self.sharedarea.small_request_threshold,
                  "malloc_size_class: too big")
        #
        # The result is simply 'free_loc_for_size[size_class]'
        result = self.free_loc_for_size[size_class]
        if not result:
            result = self._allocate_new_page(size_class)
        self.free_loc_for_size[size_class] = result.address[0]
        llarena.arena_reset(result, llmemory.sizeof(llmemory.Address), 0)
        return result
    _malloc_size_class._always_inline_ = True

    def _free_size_class(self, adr, size_class):
        """Free a single location 'adr', which is of the given size_class."""
        # just link 'adr' to the start of 'free_loc_for_size[size_class]'
        adr = llarena.getfakearenaaddress(adr)
        llarena.arena_reset(adr, size_class << WORD_POWER_2, 0)
        llarena.arena_reserve(adr, llmemory.sizeof(llmemory.Address))
        adr.address[0] = self.free_loc_for_size[size_class]
        self.free_loc_for_size[size_class] = adr
    _free_size_class._always_inline_ = True

    def _allocate_new_page(self, size_class):
        """Allocate and return a new page for the given size_class."""
        #
        sharedarea = self.sharedarea
        result = llarena.arena_malloc(sharedarea.page_size, 0)
        if not result:
            fatalerror("FIXME: Out of memory! (should raise MemoryError)")
            return NULL
        if not we_are_translated():
            self._seen_pages.add(result)
        self.count_pages += 1
        sharedarea.fetch_count_total_bytes_and_add(sharedarea.page_size)
        #
        # Initialize the fields of the resulting page
        llarena.arena_reserve(result, llmemory.sizeof(PAGE_HEADER))
        page = llmemory.cast_adr_to_ptr(result, PAGE_PTR)
        page.nextpage = self.pages_for_size[size_class]
        self.pages_for_size[size_class] = page
        #
        # Initialize the chained list in the page
        head = result + llmemory.sizeof(PAGE_HEADER)
        ll_assert(not self.free_loc_for_size[size_class],
                  "free_loc_for_size is supposed to contain NULL here")
        self.free_loc_for_size[size_class] = head
        #
        i = sharedarea.nblocks_for_size[size_class]
        nsize = size_class << WORD_POWER_2
        current = head
        while True:
            llarena.arena_reserve(current, llmemory.sizeof(llmemory.Address))
            i -= 1
            if i == 0:
                break
            next = current + nsize
            current.address[0] = next
            current = next
        current.address[0] = llmemory.NULL
        #
        return head


    def malloc_object_addr(self, totalsize):
        """Malloc.  You should also call add_regular() later, or keep it in
        some other data structure.  Note that it is not zero-filled."""
        nsize = llmemory.raw_malloc_usage(totalsize)
        if nsize <= self.sharedarea.small_request_threshold:
            size_class = (nsize + WORD - 1) >> WORD_POWER_2
            return self._malloc_size_class(size_class)
        else:
            count = llmemory.raw_malloc_usage(totalsize)
            result = llarena.arena_malloc(count, 0)
            # increment the counter *after* arena_malloc() returned
            # successfully, otherwise we might increment it of a huge
            # bogus number
            self.sharedarea.fetch_count_total_bytes_and_add(count)
            return result

    def malloc_object(self, objsize):
        totalsize = self.gc.gcheaderbuilder.size_gc_header + objsize
        addr = self.malloc_object_addr(totalsize)
        llarena.arena_reserve(addr, _dummy_size(totalsize))
        return addr + self.gc.gcheaderbuilder.size_gc_header

    def free_object(self, obj):
        adr1 = obj - self.gc.gcheaderbuilder.size_gc_header
        totalsize = (self.gc.gcheaderbuilder.size_gc_header +
                     self.gc.get_size_incl_hash(obj))
        if totalsize <= self.sharedarea.small_request_threshold:
            size_class = (totalsize + WORD_POWER_2 - 1) >> WORD_POWER_2
            self._free_size_class(adr1, size_class)
        else:
            # decrement the counter *before* we free the memory,
            # otherwise there could in theory be a race condition that
            # ends up overflowing the counter
            self.sharedarea.fetch_count_total_bytes_and_add(-totalsize)
            llarena.arena_free(llarena.getfakearenaaddress(adr1))

    def gift_all_pages_to_shared_area(self):
        """Send to the shared area all my pages.  For now we don't extract
        the information about which locations are free or not; we just stick
        them into 'full_pages' and leave it to the next global GC to figure
        them out.
        """
        stmshared = self.sharedarea
        stmshared.gc.acquire_global_lock()
        i = stmshared.length - 1
        while i >= 1:
            lpage = self.pages_for_size[i]
            if lpage:
                gpage = stmshared.full_pages[i]
                gpage_addr = llmemory.cast_ptr_to_adr(gpage)
                lpage.secondary_free_list = gpage_addr
                stmshared.full_pages[i] = lpage
            i -= 1
        stmshared.count_global_pages += self.count_pages
        stmshared.gc.release_global_lock()

    def delete(self):
        self.gift_all_pages_to_shared_area()
        lltype.free(self.free_loc_for_size, flavor='raw',
                    track_allocation=False)
        lltype.free(self.pages_for_size, flavor='raw',
                    track_allocation=False)
        free_non_gc_object(self)


# ____________________________________________________________

def _dummy_size(size):
    if we_are_translated():
        return size
    if isinstance(size, int):
        size = llmemory.sizeof(lltype.Char) * size
    return size
