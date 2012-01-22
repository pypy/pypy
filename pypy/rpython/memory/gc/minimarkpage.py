from pypy.rpython.lltypesystem import lltype, llmemory, llarena, rffi
from pypy.rlib.rarithmetic import LONG_BIT, r_uint
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import ll_assert

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
    PAGE_HEADER_SIZE_MAX = 32

    def __init__(self, arena_size, page_size, small_request_threshold):
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
        self.page_for_size = lltype.malloc(rffi.CArray(PAGE_PTR), length,
                                           flavor='raw', zero=True,
                                           immortal=True)
        self.full_page_for_size = lltype.malloc(rffi.CArray(PAGE_PTR), length,
                                                flavor='raw', zero=True,
                                                immortal=True)
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


    def allocate_big_chunk(self, arena_size):
        return llarena.arena_malloc(arena_size, False)

    def free_big_chunk(self, arena):
        llarena.arena_free(arena)


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


    def allocate_new_arena(self):
        """Loads in self.current_arena the arena to allocate from next."""
        #
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
                return
            #
            i += 1
            self.min_empty_nfreepages = i
        #
        # No more arena with any free page.  We must allocate a new arena.
        if not we_are_translated():
            for a in self._all_arenas():
                assert a.nfreepages == 0
        #
        # 'arena_base' points to the start of malloced memory; it might not
        # be a page-aligned address
        arena_base = llarena.arena_malloc(self.arena_size, False)
        if not arena_base:
            raise MemoryError("couldn't allocate the next arena")
        arena_end = arena_base + self.arena_size
        #
        # 'firstpage' points to the first unused page
        firstpage = start_of_page(arena_base + self.page_size - 1,
                                  self.page_size)
        # 'npages' is the number of full pages just allocated
        npages = (arena_end - firstpage) // self.page_size
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


    def mass_free(self, ok_to_free_func):
        """For each object, if ok_to_free_func(obj) returns True, then free
        the object.
        """
        self.total_memory_used = r_uint(0)
        #
        # For each size class:
        size_class = self.small_request_threshold >> WORD_POWER_2
        while size_class >= 1:
            #
            # Walk the pages in 'page_for_size[size_class]' and
            # 'full_page_for_size[size_class]' and free some objects.
            # Pages completely freed are added to 'page.arena.freepages',
            # and become available for reuse by any size class.  Pages
            # not completely freed are re-chained either in
            # 'full_page_for_size[]' or 'page_for_size[]'.
            self.mass_free_in_pages(size_class, ok_to_free_func)
            #
            size_class -= 1
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
                    llarena.arena_free(arena.base)
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


    def mass_free_in_pages(self, size_class, ok_to_free_func):
        nblocks = self.nblocks_for_size[size_class]
        block_size = size_class * WORD
        remaining_partial_pages = PAGE_NULL
        remaining_full_pages = PAGE_NULL
        #
        step = 0
        while step < 2:
            if step == 0:
                page = self.full_page_for_size[size_class]
            else:
                page = self.page_for_size[size_class]
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

                page = nextpage
            #
            step += 1
        #
        self.page_for_size[size_class] = remaining_partial_pages
        self.full_page_for_size[size_class] = remaining_full_pages


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
                if ok_to_free_func(obj):
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
