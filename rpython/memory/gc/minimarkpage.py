import sys
from rpython.rtyper.lltypesystem import lltype, llmemory, llarena, rffi
from rpython.rlib.rarithmetic import LONG_BIT, r_uint
from rpython.rlib.objectmodel import we_are_translated, not_rpython
from rpython.rlib.objectmodel import always_inline
from rpython.rlib.debug import ll_assert, fatalerror
from rpython.translator.tool.cbuild import ExternalCompilationInfo

WORD = LONG_BIT // 8
NULL = llmemory.NULL
WORD_POWER_2 = {32: 2, 64: 3}[LONG_BIT]
assert 1 << WORD_POWER_2 == WORD


# Terminology: the memory is subdivided into "arenas" containing "pages".
# A page contains a number of allocated objects, called "blocks".

# The actual allocation occurs in whole arenas, which are then subdivided
# into pages.  For each arena we allocate one of the following structures:

ARENA_PTR = lltype.Ptr(lltype.ForwardReference())
ARENA = lltype.Struct('ArenaReference',
    # -- The address of the arena, as returned by malloc()
    ('base', llmemory.Address),
    # -- The number of free and the total number of pages in the arena
    ('nfreepages', lltype.Signed),
    ('totalpages', lltype.Signed),
    # -- A chained list of free pages in the arena.  Ends with NULL.
    ('freepages', llmemory.Address),
    # -- A linked list of arenas.  See below.
    ('nextarena', ARENA_PTR),
    )
ARENA_PTR.TO.become(ARENA)
ARENA_NULL = lltype.nullptr(ARENA)

# The idea is that when we need a free page, we take it from the arena
# which currently has the *lowest* number of free pages.  This allows
# arenas with a lot of free pages to eventually become entirely free, at
# which point they are returned to the OS.  If an arena has a total of
# 64 pages, then we have 64 global lists, arenas_lists[0] to
# arenas_lists[63], such that arenas_lists[i] contains exactly those
# arenas that have 'nfreepages == i'.  We allocate pages out of the
# arena in 'current_arena'; when it is exhausted we pick another arena
# with the smallest value for nfreepages (but > 0).

# ____________________________________________________________
#
# Each page in an arena can be:
#
# - uninitialized: never touched so far.
#
# - allocated: contains some objects (all of the same size).  Starts with a
#   PAGE_HEADER.  The page is on the chained list of pages that still have
#   room for objects of that size, unless it is completely full.
#
# - free: used to be partially full, and is now free again.  The page is
#   on the chained list of free pages 'freepages' from its arena.

# Each allocated page contains blocks of a given size, which can again be in
# one of three states: allocated, free, or uninitialized.  The uninitialized
# blocks (initially all of them) are at the tail of the page.

PAGE_PTR = lltype.Ptr(lltype.ForwardReference())
PAGE_HEADER = lltype.Struct('PageHeader',
    # -- The following pointer makes a chained list of pages.  For non-full
    #    pages, it is a chained list of pages having the same size class,
    #    rooted in 'page_for_size[size_class]'.  For full pages, it is a
    #    different chained list rooted in 'full_page_for_size[size_class]'.
    #    For free pages, it is the list 'freepages' in the arena header.
    ('nextpage', PAGE_PTR),
    # -- The arena this page is part of.
    ('arena', ARENA_PTR),
    # -- The number of free blocks.  The numbers of uninitialized and
    #    allocated blocks can be deduced from the context if needed.
    ('nfree', lltype.Signed),
    # -- The chained list of free blocks.  It ends as a pointer to the
    #    first uninitialized block (pointing to data that is uninitialized,
    #    or to the end of the page).
    ('freeblock', llmemory.Address),
    # -- The structure above is 4 words, which is a good value:
    #    '(1024-4) % N' is zero or very small for various small N's,
    #    i.e. there is not much wasted space.
    )
PAGE_PTR.TO.become(PAGE_HEADER)
PAGE_NULL = lltype.nullptr(PAGE_HEADER)

# ----------


class ArenaCollection(object):
    _alloc_flavor_ = "raw"

    @not_rpython
    def __init__(self, arena_size, page_size, small_request_threshold,
                 offline_visited_flags=False):
        # If we ask for 'offline_visited_flags', then we'll allocate
        # arenas that are always OFFL_RATIO pages in size, and fully aligned.
        # In this case, page_size should be 4096 or 8192.  The first page is
        # used for the offline_visited_flags.  See rpy_allocate_new_arena().
        if offline_visited_flags:
            arena_size = OFFL_ARENA_SIZE - OFFL_SYSTEM_PAGE_SIZE
        self.offline_visited_flags = offline_visited_flags
        #
        # 'small_request_threshold' is the largest size that we
        # can ask with self.malloc().
        self.arena_size = arena_size
        self.page_size = page_size
        self.small_request_threshold = small_request_threshold
        #
        # 'pageaddr_for_size': for each size N between WORD and
        # small_request_threshold (included), contains either NULL or
        # a pointer to a page that has room for at least one more
        # allocation of the given size.
        length = small_request_threshold / WORD + 1
        self.page_for_size          = self._new_page_ptr_list(length)
        self.full_page_for_size     = self._new_page_ptr_list(length)
        self.old_page_for_size      = self._new_page_ptr_list(length)
        self.old_full_page_for_size = self._new_page_ptr_list(length)
        self.nblocks_for_size = lltype.malloc(rffi.CArray(lltype.Signed),
                                              length, flavor='raw',
                                              immortal=True)
        self.hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))
        assert page_size > self.hdrsize
        self.nblocks_for_size[0] = 0    # unused
        for i in range(1, length):
            self.nblocks_for_size[i] = (page_size - self.hdrsize) // (WORD * i)
        #
        self.max_pages_per_arena = arena_size // page_size
        self.arenas_lists = lltype.malloc(rffi.CArray(ARENA_PTR),
                                          self.max_pages_per_arena,
                                          flavor='raw', zero=True,
                                          immortal=True)
        # this is used in mass_free() only
        self.old_arenas_lists = lltype.malloc(rffi.CArray(ARENA_PTR),
                                              self.max_pages_per_arena,
                                              flavor='raw', zero=True,
                                              immortal=True)
        #
        # the arena currently consumed; it must have at least one page
        # available, or be NULL.  The arena object that we point to is
        # not in any 'arenas_lists'.  We will consume all its pages before
        # we choose a next arena, even if there is a major collection
        # in-between.
        self.current_arena = ARENA_NULL
        #
        # guarantee that 'arenas_lists[1:min_empty_nfreepages]' are all empty
        self.min_empty_nfreepages = self.max_pages_per_arena
        #
        # part of current_arena might still contain uninitialized pages
        self.num_uninitialized_pages = 0
        #
        # the total memory used, counting every block in use, without
        # the additional bookkeeping stuff.
        self.total_memory_used = r_uint(0)


    def _new_page_ptr_list(self, length):
        return lltype.malloc(rffi.CArray(PAGE_PTR), length,
                             flavor='raw', zero=True,
                             immortal=True)


    def malloc(self, size):
        """Allocate a block from a page in an arena."""
        nsize = llmemory.raw_malloc_usage(size)
        ll_assert(nsize > 0, "malloc: size is null or negative")
        ll_assert(nsize <= self.small_request_threshold,"malloc: size too big")
        ll_assert((nsize & (WORD-1)) == 0, "malloc: size is not aligned")
        self.total_memory_used += r_uint(nsize)
        #
        # Get the page to use from the size
        size_class = nsize >> WORD_POWER_2
        page = self.page_for_size[size_class]
        if page == PAGE_NULL:
            page = self.allocate_new_page(size_class)
        #
        # The result is simply 'page.freeblock'
        result = page.freeblock
        if page.nfree > 0:
            #
            # The 'result' was part of the chained list; read the next.
            page.nfree -= 1
            freeblock = result.address[0]
            llarena.arena_reset(result,
                                llmemory.sizeof(llmemory.Address),
                                0)
            #
        else:
            # The 'result' is part of the uninitialized blocks.
            freeblock = result + nsize
        #
        page.freeblock = freeblock
        #
        pageaddr = llarena.getfakearenaaddress(llmemory.cast_ptr_to_adr(page))
        if freeblock - pageaddr > self.page_size - nsize:
            # This was the last free block, so unlink the page from the
            # chained list and put it in the 'full_page_for_size' list.
            self.page_for_size[size_class] = page.nextpage
            page.nextpage = self.full_page_for_size[size_class]
            self.full_page_for_size[size_class] = page
        #
        llarena.arena_reserve(result, _dummy_size(size))
        return result


    def allocate_new_page(self, size_class):
        """Allocate and return a new page for the given size_class."""
        #
        # Allocate a new arena if needed.
        if self.current_arena == ARENA_NULL:
            self.allocate_new_arena()
        #
        # The result is simply 'current_arena.freepages'.
        arena = self.current_arena
        result = arena.freepages
        if arena.nfreepages > 0:
            #
            # The 'result' was part of the chained list; read the next.
            arena.nfreepages -= 1
            freepages = result.address[0]
            llarena.arena_reset(result,
                                llmemory.sizeof(llmemory.Address),
                                0)
            #
        else:
            # The 'result' is part of the uninitialized pages.
            ll_assert(self.num_uninitialized_pages > 0,
                      "fully allocated arena found in self.current_arena")
            self.num_uninitialized_pages -= 1
            if self.num_uninitialized_pages > 0:
                freepages = result + self.page_size
            else:
                freepages = NULL
        #
        arena.freepages = freepages
        if freepages == NULL:
            # This was the last page, so put the arena away into
            # arenas_lists[0].
            ll_assert(arena.nfreepages == 0, 
                      "freepages == NULL but nfreepages > 0")
            arena.nextarena = self.arenas_lists[0]
            self.arenas_lists[0] = arena
            self.current_arena = ARENA_NULL
        #
        # Initialize the fields of the resulting page
        llarena.arena_reserve(result, llmemory.sizeof(PAGE_HEADER))
        page = llmemory.cast_adr_to_ptr(result, PAGE_PTR)
        page.arena = arena
        page.nfree = 0
        page.freeblock = result + self.hdrsize
        page.nextpage = PAGE_NULL
        ll_assert(self.page_for_size[size_class] == PAGE_NULL,
                  "allocate_new_page() called but a page is already waiting")
        self.page_for_size[size_class] = page
        return page


    def _all_arenas(self):
        """For testing.  Enumerates all arenas."""
        if self.current_arena:
            yield self.current_arena
        for arena in self.arenas_lists:
            while arena:
                yield arena
                arena = arena.nextarena


    def _pick_next_arena(self):
        # Pick an arena from 'arenas_lists[i]', with i as small as possible
        # but > 0.  Use caching with 'min_empty_nfreepages', which guarantees
        # that 'arenas_lists[1:min_empty_nfreepages]' are all empty.
        i = self.min_empty_nfreepages
        while i < self.max_pages_per_arena:
            #
            if self.arenas_lists[i] != ARENA_NULL:
                #
                # Found it.
                self.current_arena = self.arenas_lists[i]
                self.arenas_lists[i] = self.current_arena.nextarena
                return True
            #
            i += 1
            self.min_empty_nfreepages = i
        return False


    def allocate_new_arena(self):
        """Loads in self.current_arena the arena to allocate from next."""
        #
        if self._pick_next_arena():
            return
        #
        # Maybe we are incrementally collecting, in which case an arena
        # could have more free pages thrown into it than arenas_lists[]
        # accounts for.  Rehash and retry.
        self._rehash_arenas_lists()
        if self._pick_next_arena():
            return
        #
        # No more arena with any free page.  We must allocate a new arena.
        if not we_are_translated():
            for a in self._all_arenas():
                assert a.nfreepages == 0

        if not self.offline_visited_flags:
            #
            # 'arena_base' points to the start of malloced memory; it might not
            # be a page-aligned address
            arena_base = llarena.arena_malloc(self.arena_size, False)
            if not arena_base:
                out_of_memory("out of memory: couldn't allocate the next arena")
            arena_end = arena_base + self.arena_size
            #
            # 'firstpage' points to the first unused page
            firstpage = start_of_page(arena_base + self.page_size - 1,
                                      self.page_size)
        else:
            assert OFFL_SYSTEM_PAGE_SIZE == llarena.posixpagesize.get()
            arena_base = rpy_allocate_new_arena()
            arena_end = arena_base + OFFL_ARENA_SIZE
            firstpage = arena_base + max(self.page_size, OFFL_SYSTEM_PAGE_SIZE)
        #
        # 'npages' is the number of full pages just allocated
        npages = (arena_end - firstpage) // self.page_size

        if not we_are_translated():
            arena_base.arena._from_minimarkpage = True
        #
        # Allocate an ARENA object and initialize it
        arena = lltype.malloc(ARENA, flavor='raw', track_allocation=False)
        arena.base = arena_base
        arena.nfreepages = 0        # they are all uninitialized pages
        arena.totalpages = npages
        arena.freepages = firstpage
        self.num_uninitialized_pages = npages
        self.current_arena = arena
        #
    allocate_new_arena._dont_inline_ = True


    def mass_free_prepare(self):
        """Prepare calls to mass_free_incremental(): moves the chained lists
        into 'self.old_xxx'.
        """
        self.total_memory_used = r_uint(0)
        #
        size_class = self.small_request_threshold >> WORD_POWER_2
        self.size_class_with_old_pages = size_class
        #
        while size_class >= 1:
            self.old_page_for_size[size_class]      = (
                            self.page_for_size[size_class])
            self.old_full_page_for_size[size_class] = (
                            self.full_page_for_size[size_class])
            self.page_for_size[size_class]      = PAGE_NULL
            self.full_page_for_size[size_class] = PAGE_NULL
            size_class -= 1


    def mass_free_incremental(self, ok_to_free_func, max_pages):
        """For each object, if ok_to_free_func(obj) returns True, then free
        the object.  This returns True if complete, or False if the limit
        'max_pages' is reached.
        """
        size_class = self.size_class_with_old_pages
        #
        while size_class >= 1:
            #
            # Walk the pages in 'page_for_size[size_class]' and
            # 'full_page_for_size[size_class]' and free some objects.
            # Pages completely freed are added to 'page.arena.freepages',
            # and become available for reuse by any size class.  Pages
            # not completely freed are re-chained either in
            # 'full_page_for_size[]' or 'page_for_size[]'.
            max_pages = self.mass_free_in_pages(size_class, ok_to_free_func,
                                                max_pages)
            if max_pages <= 0:
                self.size_class_with_old_pages = size_class
                return False
            #
            size_class -= 1
        #
        if size_class >= 0:
            self._rehash_arenas_lists()
            self.size_class_with_old_pages = -1
        #
        return True


    def mass_free(self, ok_to_free_func):
        """For each object, if ok_to_free_func(obj) returns True, then free
        the object.
        """
        self.mass_free_prepare()
        #
        res = self.mass_free_incremental(ok_to_free_func, sys.maxint)
        ll_assert(res, "non-incremental mass_free_in_pages() returned False")


    def _rehash_arenas_lists(self):
        #
        # Rehash arenas into the correct arenas_lists[i].  If
        # 'self.current_arena' contains an arena too, it remains there.
        (self.old_arenas_lists, self.arenas_lists) = (
            self.arenas_lists, self.old_arenas_lists)
        #
        i = 0
        while i < self.max_pages_per_arena:
            self.arenas_lists[i] = ARENA_NULL
            i += 1
        #
        i = 0
        while i < self.max_pages_per_arena:
            arena = self.old_arenas_lists[i]
            while arena != ARENA_NULL:
                nextarena = arena.nextarena
                #
                if arena.nfreepages == arena.totalpages:
                    #
                    # The whole arena is empty.  Free it.
                    llarena.arena_reset(arena.base, self.arena_size, 4)
                    if not self.offline_visited_flags:
                        llarena.arena_free(arena.base)
                    else:
                        rpy_free_arena(arena.base)
                    lltype.free(arena, flavor='raw', track_allocation=False)
                    #
                else:
                    # Insert 'arena' in the correct arenas_lists[n]
                    n = arena.nfreepages
                    ll_assert(n < self.max_pages_per_arena,
                             "totalpages != nfreepages >= max_pages_per_arena")
                    arena.nextarena = self.arenas_lists[n]
                    self.arenas_lists[n] = arena
                #
                arena = nextarena
            i += 1
        #
        self.min_empty_nfreepages = 1


    def mass_free_in_pages(self, size_class, ok_to_free_func, max_pages):
        nblocks = self.nblocks_for_size[size_class]
        block_size = size_class * WORD
        remaining_partial_pages = self.page_for_size[size_class]
        remaining_full_pages = self.full_page_for_size[size_class]
        #
        step = 0
        while step < 2:
            if step == 0:
                page = self.old_full_page_for_size[size_class]
                self.old_full_page_for_size[size_class] = PAGE_NULL
            else:
                page = self.old_page_for_size[size_class]
                self.old_page_for_size[size_class] = PAGE_NULL
            #
            while page != PAGE_NULL:
                #
                # Collect the page.
                surviving = self.walk_page(page, block_size, ok_to_free_func)
                nextpage = page.nextpage
                #
                if surviving == nblocks:
                    #
                    # The page is still full.  Re-insert it in the
                    # 'remaining_full_pages' chained list.
                    ll_assert(step == 0,
                              "A non-full page became full while freeing")
                    page.nextpage = remaining_full_pages
                    remaining_full_pages = page
                    #
                elif surviving > 0:
                    #
                    # There is at least 1 object surviving.  Re-insert
                    # the page in the 'remaining_partial_pages' chained list.
                    page.nextpage = remaining_partial_pages
                    remaining_partial_pages = page
                    #
                else:
                    # No object survives; free the page.
                    self.free_page(page)

                #
                max_pages -= 1
                if max_pages <= 0:
                    # End of the incremental step: store back the unprocessed
                    # pages into self.old_xxx and return early
                    if step == 0:
                        self.old_full_page_for_size[size_class] = nextpage
                    else:
                        self.old_page_for_size[size_class] = nextpage
                    step = 99     # stop
                    break

                page = nextpage
            #
            else:
                step += 1
        #
        self.page_for_size[size_class] = remaining_partial_pages
        self.full_page_for_size[size_class] = remaining_full_pages
        return max_pages


    def free_page(self, page):
        """Free a whole page."""
        #
        # Insert the freed page in the arena's 'freepages' list.
        # If nfreepages == totalpages, then it will be freed at the
        # end of mass_free().
        arena = page.arena
        arena.nfreepages += 1
        pageaddr = llmemory.cast_ptr_to_adr(page)
        pageaddr = llarena.getfakearenaaddress(pageaddr)
        llarena.arena_reset(pageaddr, self.page_size, 0)
        llarena.arena_reserve(pageaddr, llmemory.sizeof(llmemory.Address))
        pageaddr.address[0] = arena.freepages
        arena.freepages = pageaddr


    def walk_page(self, page, block_size, ok_to_free_func):
        """Walk over all objects in a page, and ask ok_to_free_func()."""
        #
        # 'freeblock' is the next free block
        freeblock = page.freeblock
        #
        # 'prevfreeblockat' is the address of where 'freeblock' was read from.
        prevfreeblockat = lltype.direct_fieldptr(page, 'freeblock')
        prevfreeblockat = llmemory.cast_ptr_to_adr(prevfreeblockat)
        #
        obj = llarena.getfakearenaaddress(llmemory.cast_ptr_to_adr(page))
        obj += self.hdrsize
        surviving = 0    # initially
        skip_free_blocks = page.nfree
        #
        vblocknext = r_uint(0)
        vblock = rffi.cast(rffi.ULONGLONG, -1)
        #
        while True:
            #
            if obj == freeblock:
                #
                if skip_free_blocks == 0:
                    #
                    # 'obj' points to the first uninitialized block,
                    # or to the end of the page if there are none.
                    break
                #
                # 'obj' points to a free block.  It means that
                # 'prevfreeblockat.address[0]' does not need to be updated.
                # Just read the next free block from 'obj.address[0]'.
                skip_free_blocks -= 1
                prevfreeblockat = obj
                freeblock = obj.address[0]
                #
            else:
                # 'obj' points to a valid object.
                ll_assert(freeblock > obj,
                          "freeblocks are linked out of order")
                #
                if self.offline_visited_flags:
                    if self.visited_flags_limit_reached(obj, vblocknext):
                        vblocknext = (
                            self.get_64bit_limit_for_next_visited_flags(obj))
                        vblock = self.fetch_64bit_visited_flags(obj)
                    vblockmask = self.get_64bit_mask_visited_flag(obj)
                    ok = not (vblock & vblockmask)
                else:
                    ok = ok_to_free_func(obj)
                if ok:
                    #
                    # The object should die.
                    llarena.arena_reset(obj, _dummy_size(block_size), 0)
                    llarena.arena_reserve(obj,
                                          llmemory.sizeof(llmemory.Address))
                    # Insert 'obj' in the linked list of free blocks.
                    prevfreeblockat.address[0] = obj
                    prevfreeblockat = obj
                    obj.address[0] = freeblock
                    #
                    # Update the number of free objects in the page.
                    page.nfree += 1
                    #
                else:
                    # The object survives.
                    surviving += 1
            #
            obj += block_size
        #
        # Update the global total size of objects.
        self.total_memory_used += r_uint(surviving * block_size)
        #
        # Return the number of surviving objects.
        return surviving


    def _nuninitialized(self, page, size_class):
        # Helper for debugging: count the number of uninitialized blocks
        freeblock = page.freeblock
        for i in range(page.nfree):
            freeblock = freeblock.address[0]
        assert freeblock != NULL
        pageaddr = llarena.getfakearenaaddress(llmemory.cast_ptr_to_adr(page))
        num_initialized_blocks, rem = divmod(
            freeblock - pageaddr - self.hdrsize, size_class * WORD)
        assert rem == 0, "page size_class misspecified?"
        nblocks = self.nblocks_for_size[size_class]
        return nblocks - num_initialized_blocks


    @not_rpython
    def _is_inside_minimarkpage(self, hdr):
        # check that getfakearenaaddress() works and the
        # arena is flagged as "from minimarkpage"
        try:
            arena = llarena.getfakearenaaddress(hdr).arena
        except RuntimeError:
            return False
        return getattr(arena, '_from_minimarkpage', False)


    @staticmethod
    @always_inline
    def get_64bit_ptr_visited_flags(obj):
        numeric = rffi.cast(lltype.Unsigned, obj)
        base = rffi.cast(rffi.CCHARP, numeric & ~(OFFL_ARENA_SIZE - 1))
        ofs = (numeric // OFFL_RATIO) & (OFFL_SYSTEM_PAGE_SIZE - 8)
        return rffi.cast(rffi.ULONGLONGP, rffi.ptradd(base, ofs))

    @staticmethod
    @always_inline
    def get_64bit_mask_visited_flag(obj):
        numeric = rffi.cast(lltype.Unsigned, obj)
        shift = (numeric // (OFFL_RATIO/8)) & 63
        return rffi.cast(rffi.ULONGLONG, 1) << shift

    @staticmethod
    @always_inline
    def get_visited(obj):
        """test the visited flag corresponding to 'obj'"""
        p = ArenaCollection.get_64bit_ptr_visited_flags(obj)
        mask = ArenaCollection.get_64bit_mask_visited_flag(obj)
        return (p[0] & mask) != 0

    @staticmethod
    @always_inline
    def set_visited(obj):
        """set (to 1) the visited flag corresponding to 'obj'"""
        p = ArenaCollection.get_64bit_ptr_visited_flags(obj)
        mask = ArenaCollection.get_64bit_mask_visited_flag(obj)
        p[0] |= mask

    @staticmethod
    @always_inline
    def clear_visited(obj):
        """clear the visited flag corresponding to 'obj'"""
        # (Note: should not be used too often.  Due to the fact that the
        # same flag might be used for two objects if they are a single
        # word each, this might occasionally clear too much.  It is
        # still fine in this case because we clear the flag only to
        # force re-visiting the object later during major collection)
        p = ArenaCollection.get_64bit_ptr_visited_flags(obj)
        mask = ArenaCollection.get_64bit_mask_visited_flag(obj)
        p[0] &= ~mask

    @staticmethod
    @always_inline
    def get_64bit_limit_for_next_visited_flags(obj):
        """get a result that encodes the last possible position of an
        object after 'obj' where the corresponding visited flag is in
        the same 64-bit block as 'obj'."""
        numeric = rffi.cast(lltype.Unsigned, obj)
        return numeric | (64 * OFFL_RATIO / 8 - 1)

    @staticmethod
    @always_inline
    def visited_flags_limit_reached(obj, vblocknext):
        """return True if 'obj' is beyond the limit computed by
        get_64bit_limit_for_next_visited_flags()."""
        return rffi.cast(lltype.Unsigned, obj) > vblocknext

    @staticmethod
    @always_inline
    def fetch_64bit_visited_flags(obj):
        p = ArenaCollection.get_64bit_ptr_visited_flags(obj)
        result = p[0]
        p[0] = rffi.cast(rffi.ULONGLONG, 0)
        return result


# ____________________________________________________________
# Helpers to go from a pointer to the start of its page

def start_of_page(addr, page_size):
    """Return the address of the start of the page that contains 'addr'."""
    if we_are_translated():
        offset = llmemory.cast_adr_to_int(addr) % page_size
        return addr - offset
    else:
        return _start_of_page_untranslated(addr, page_size)

def _start_of_page_untranslated(addr, page_size):
    assert isinstance(addr, llarena.fakearenaaddress)
    shift = WORD  # for testing, we assume that the whole arena is not
                  # on a page boundary
    ofs = ((addr.offset - shift) // page_size) * page_size + shift
    return llarena.fakearenaaddress(addr.arena, ofs)

def _dummy_size(size):
    if we_are_translated():
        return size
    if isinstance(size, int):
        size = llmemory.sizeof(lltype.Char) * size
    return size

def out_of_memory(errmsg):
    """Signal a fatal out-of-memory error and abort.  For situations where
    it is hard to write and test code that would handle a MemoryError
    exception gracefully.
    """
    fatalerror(errmsg)


# ____________________________________________________________
# Helpers for the 'offline visited flags' mode


# xxx make the number 4096 not hard-coded, but it has implications on
# the other numbers too
OFFL_SYSTEM_PAGE_SIZE = 4096
OFFL_RATIO = WORD * 2 * 8
OFFL_ARENA_SIZE = OFFL_SYSTEM_PAGE_SIZE * OFFL_RATIO

# Idea: mmap N bytes, where N is just smaller than '2 * arena_size'.
# This is just the right size to ensure that the allocated region
# contains exactly one block of 'arena_size' pages that is fully
# aligned to an address multiple of 'arena_size'.  Then we munmap
# the extra bits at both ends.  This approach should ensure that
# after the first arena was allocated, the next one is likely to be
# placed by the system either just before or just after it; when
# it is the case, the side that connects with the previous arena
# is aligned already, and so we only have to remove the extra bit
# at the other end.  This should ensure that our aligned arenas
# grow next to each other (and in a single VMA, in Linux terms).

# The number OFFL_RATIO comes from the fact that we can use one
# visited bit for every two words of memory.  Most objects are at
# least two words in length.  If we have a page that contains
# single-word objects, then the visited bits clash: the same bit
# is used for two objects.  However, that's a very minor problem,
# because the objects are too small to contain further references
# anyway, so at most we leak one of the two objects when the other
# is still in use (i.e. at most one word of memory per word-sized
# object alive).  So, OFFL_RATIO is equal to 64 on 32-bit and 128
# on 64-bit machines.  That's also equal to the number of pages in
# one arena: we reserve the first page for visited bits, and all
# remaining pages are used for real objects.

eci = ExternalCompilationInfo(
    post_include_bits=[
        'RPY_EXTERN void *rpy_allocate_new_arena(void);',
        'RPY_EXTERN void rpy_free_arena(void *);',
        'RPY_EXTERN char rpy_get_visited(void *);',
        'RPY_EXTERN void rpy_set_visited(void *);',
        'RPY_EXTERN void rpy_clear_visited(void *);',
        ],
    separate_module_sources=['''
#include <stdlib.h>
#include <sys/mman.h>

#define OFFL_SYSTEM_PAGE_SIZE  %(OFFL_SYSTEM_PAGE_SIZE)d
#define OFFL_RATIO             %(OFFL_RATIO)d
#define OFFL_ARENA_SIZE        %(OFFL_ARENA_SIZE)d

RPY_EXTERN void *rpy_allocate_new_arena(void)
{
    size_t arena_size = OFFL_ARENA_SIZE;
    size_t map_size = arena_size * 2 - OFFL_SYSTEM_PAGE_SIZE;
    void *p = mmap(NULL, map_size, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) {
        perror("Fatal RPython error: out of memory");
        abort();
    }

    char *result = (char *)((((long)p) + arena_size - 1) & ~(arena_size-1));
    if (result > (char *)p)
        munmap(p, result - (char *)p);
    long free_end = ((char *)p + map_size) - (result + arena_size);
    if (free_end > 0)
        munmap(result + arena_size, free_end);

    /* 'result' is freshly mmap()ed so it contains zeroes at this point */
    return result;
}

RPY_EXTERN void rpy_free_arena(void *base)
{
    munmap(base, OFFL_ARENA_SIZE);
}
''' % globals()])

rpy_allocate_new_arena = rffi.llexternal(
    'rpy_allocate_new_arena', [], llmemory.Address,
    compilation_info=eci, _nowrapper=True)

rpy_free_arena = rffi.llexternal(
    'rpy_free_arena', [llmemory.Address], lltype.Void,
    compilation_info=eci, _nowrapper=True)
