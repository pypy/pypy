"""
This is a variant of minimarkpage.py, for the case of a 64-bit translation
with --compressptr.  xxx it should not be a whole copy
"""
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, rffi
from pypy.rlib.rarithmetic import LONG_BIT, r_uint
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import ll_assert
from pypy.rlib import rmmap

WORD = LONG_BIT // 8
NULL = llmemory.NULL
WORD_POWER_2 = {32: 2, 64: 3}[LONG_BIT]
assert 1 << WORD_POWER_2 == WORD


# Terminology: the memory is subdivided into "arenas" containing "pages".
# A page contains a number of allocated objects, called "blocks".

# The actual allocation occurs in whole arenas, which are then subdivided
# into pages.  Arenas are allocated (after translation to C) as an mmap()
# at fixed addresses:

ARENA_SIZE       = 0x100000      # 1MB
ARENA_ADDR_START = 0x10000000    # 256MB  (too low a number, segfault on linux)
ARENA_ADDR_STOP  = 0x800000000   # 32GB

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
    #    For free pages, it is the list 'freepages'.
    ('nextpage', PAGE_PTR),
    # -- The number of free blocks.  The numbers of uninitialized and
    #    allocated blocks can be deduced from the context if needed.
    ('nfree', rffi.INT),
    # -- The chained list of free blocks.  It ends as a reference to the
    #    first uninitialized block (pointing to data that is uninitialized,
    #    or to the end of the page).  Each entry in the free list is encoded
    #    as an offset to the start of the page.
    ('freeblock', rffi.INT),
    # -- The structure above is 2 words, which is a good value:
    #    '(512-2) % N' is zero or very small for various small N's,
    #    i.e. there is not much wasted space.
    )
PAGE_HEADER_SIZE_MAX = 16      # the PAGE_HEADER is at most 16 bytes
PAGE_PTR.TO.become(PAGE_HEADER)
PAGE_NULL = lltype.nullptr(PAGE_HEADER)

FREEBLOCK = lltype.Struct('FreeBlock', ('freeblock', rffi.INT))
FREEBLOCK_PTR = lltype.Ptr(FREEBLOCK)

# ----------


class ArenaCollection2(object):
    _alloc_flavor_ = "raw"
    PAGE_HEADER_SIZE_MAX = PAGE_HEADER_SIZE_MAX

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
        # The next address to get an arena from
        self.next_arena_addr = ARENA_ADDR_START
        #
        # Uninitialized pages from the current arena
        self.next_uninitialized_page = NULL
        self.num_uninitialized_pages = 0
        #
        # the total memory used, counting every block in use, without
        # the additional bookkeeping stuff.
        self.total_memory_used = r_uint(0)
        #
        # Chained list of pages that used to contain stuff but are now free.
        self.freepages = NULL


    def malloc(self, size):
        """Allocate a block from a page in an arena."""
        nsize = llmemory.raw_malloc_usage(size)
        ll_assert(nsize > 0, "malloc: size is null or negative")
        ll_assert(nsize <= self.small_request_threshold,"malloc: size too big")
        ll_assert((nsize & (WORD-1)) == 0, "malloc: size is not aligned")
        self.total_memory_used += nsize
        #
        # Get the page to use from the size
        size_class = nsize >> WORD_POWER_2
        page = self.page_for_size[size_class]
        if page == PAGE_NULL:
            page = self.allocate_new_page(size_class)
        #
        # The result is simply 'page.freeblock'
        pageaddr = llarena.getfakearenaaddress(llmemory.cast_ptr_to_adr(page))
        resultofs = rffi.getintfield(page, 'freeblock')
        result = pageaddr + resultofs
        page_nfree = rffi.getintfield(page, 'nfree')
        if page_nfree > 0:
            #
            # The 'result' was part of the chained list; read the next.
            page_nfree -= 1
            rffi.setintfield(page, 'nfree', page_nfree)
            freeblockptr = llmemory.cast_adr_to_ptr(result, FREEBLOCK_PTR)
            freeblock = rffi.getintfield(freeblockptr, 'freeblock')
            llarena.arena_reset(result,
                                llmemory.sizeof(FREEBLOCK),
                                0)
            #
        else:
            # The 'result' is part of the uninitialized blocks.
            freeblock = resultofs + nsize
        #
        rffi.setintfield(page, 'freeblock', freeblock)
        #
        if freeblock > self.page_size - nsize:
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
        # If available, return the next page in self.freepages
        if self.freepages != NULL:
            result = self.freepages
            self.freepages = result.address[0]
            llarena.arena_reset(result,
                                llmemory.sizeof(llmemory.Address),
                                0)
            #
        else:
            #
            # No more free page.  Allocate a new arena if needed.
            if self.next_uninitialized_page == NULL:
                self.allocate_new_arena()
            #
            # The result is simply 'self.next_uninitialized_page'.
            result = self.next_uninitialized_page
            #
            ll_assert(self.num_uninitialized_pages > 0,
                      "fully allocated arena found in next_uninitialized_page")
            self.num_uninitialized_pages -= 1
            if self.num_uninitialized_pages > 0:
                freepages = result + self.page_size
            else:
                freepages = NULL
            #
            self.next_uninitialized_page = freepages
        #
        # Initialize the fields of the resulting page
        llarena.arena_reserve(result, llmemory.sizeof(PAGE_HEADER))
        page = llmemory.cast_adr_to_ptr(result, PAGE_PTR)
        rffi.setintfield(page, 'nfree', 0)
        rffi.setintfield(page, 'freeblock', self.hdrsize)
        page.nextpage = PAGE_NULL
        ll_assert(self.page_for_size[size_class] == PAGE_NULL,
                  "allocate_new_page() called but a page is already waiting")
        self.page_for_size[size_class] = page
        return page


    def allocate_new_arena(self):
        """Allocates an arena and load it in self.next_uninitialized_page."""
        arena_base = self.allocate_big_chunk(self.arena_size)
        self.next_uninitialized_page = arena_base
        self.num_uninitialized_pages = self.arena_size // self.page_size
    allocate_new_arena._dont_inline_ = True

    def allocate_big_chunk(self, arena_size):
        if we_are_translated():
            return self._allocate_new_arena_mmap(arena_size)
        else:
            return llarena.arena_malloc(arena_size, False)

    def free_big_chunk(self, arena):
        if we_are_translated():
            pass     # good enough
        else:
            llarena.arena_free(arena)

    def _allocate_new_arena_mmap(self, arena_size):
        #
        # Round up the number in arena_size.
        arena_size = (arena_size + ARENA_SIZE - 1) & ~(ARENA_SIZE-1)
        #
        # Try to mmap() at a MAP_FIXED address, in a 'while' loop until it
        # succeeds.  The important part is that it must return an address
        # that is in the lower 32GB of the addressable space.
        while 1:
            addr = self.next_arena_addr
            if addr + arena_size > ARENA_ADDR_STOP:
                raise MemoryError("exhausted the 32GB of memory")
            self.next_arena_addr = addr + arena_size
            flags = rmmap.MAP_PRIVATE | rmmap.MAP_ANONYMOUS | rmmap.MAP_FIXED
            prot = rmmap.PROT_READ | rmmap.PROT_WRITE
            arena_base = rmmap.c_mmap_safe(rffi.cast(rffi.CCHARP, addr),
                                           arena_size, prot, flags, -1, 0)
            if arena_base != rffi.cast(rffi.CCHARP, -1):
                break
        #
        # 'arena_base' points to the start of mmap()ed memory.
        # Sanity-check it.
        if rffi.cast(lltype.Unsigned, arena_base) >= ARENA_ADDR_STOP:
            raise MMapIgnoredFIXED("mmap() ignored the MAP_FIXED and returned"
                                   " an address that is not in the first 32GB")
        #
        return rffi.cast(llmemory.Address, arena_base)


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
            # Pages completely freed are added to 'self.freepages',
            # and become available for reuse by any size class.  Pages
            # not completely freed are re-chained either in
            # 'full_page_for_size[]' or 'page_for_size[]'.
            if (self.full_page_for_size[size_class] != PAGE_NULL or
                self.page_for_size[size_class] != PAGE_NULL):
                self.mass_free_in_pages(size_class, ok_to_free_func)
            #
            size_class -= 1


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
        # Insert the freed page in the 'freepages' list.
        pageaddr = llmemory.cast_ptr_to_adr(page)
        pageaddr = llarena.getfakearenaaddress(pageaddr)
        llarena.arena_reset(pageaddr, self.page_size, 0)
        llarena.arena_reserve(pageaddr, llmemory.sizeof(llmemory.Address))
        pageaddr.address[0] = self.freepages
        self.freepages = pageaddr


    def walk_page(self, page, block_size, ok_to_free_func):
        """Walk over all objects in a page, and ask ok_to_free_func()."""
        #
        pageaddr = llarena.getfakearenaaddress(llmemory.cast_ptr_to_adr(page))
        #
        # 'freeblock' is the next free block
        freeblock = pageaddr + rffi.getintfield(page, 'freeblock')
        #
        # 'prevfreeblockat' is the address of where 'freeblock' was read from.
        prevfreeblockat = lltype.direct_fieldptr(page, 'freeblock')
        #
        obj = pageaddr + self.hdrsize
        surviving = 0    # initially
        skip_free_blocks = rffi.getintfield(page, 'nfree')
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
                # 'prevfreeblockat[0]' does not need to be updated.
                # Just read the next free block from 'obj.address[0]'.
                skip_free_blocks -= 1
                prevfreeblockat = llmemory.cast_adr_to_ptr(obj, FREEBLOCK_PTR)
                freeblock = pageaddr + rffi.getintfield(prevfreeblockat,
                                                        'freeblock')
                prevfreeblockat = lltype.direct_fieldptr(prevfreeblockat,
                                                         'freeblock')
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
                    llarena.arena_reserve(obj, llmemory.sizeof(FREEBLOCK))
                    # Insert 'obj' in the linked list of free blocks.
                    prevfreeblockat[0] = rffi.cast(rffi.INT, obj - pageaddr)
                    prevfreeblockat = llmemory.cast_adr_to_ptr(obj,
                                                               FREEBLOCK_PTR)
                    prevfreeblockat.freeblock = rffi.cast(rffi.INT,
                                                          freeblock - pageaddr)
                    prevfreeblockat = lltype.direct_fieldptr(prevfreeblockat,
                                                             'freeblock')
                    #
                    # Update the number of free objects in the page.
                    page_nfree = rffi.getintfield(page, 'nfree')
                    page_nfree += 1
                    rffi.setintfield(page, 'nfree', page_nfree)
                    #
                else:
                    # The object survives.
                    surviving += 1
            #
            obj += block_size
        #
        # Update the global total size of objects.
        self.total_memory_used += surviving * block_size
        #
        # Return the number of surviving objects.
        return surviving


    def _nuninitialized(self, page, size_class):
        # Helper for debugging: count the number of uninitialized blocks
        freeblock = rffi.getintfield(page, 'freeblock')
        pageaddr = llmemory.cast_ptr_to_adr(page)
        pageaddr = llarena.getfakearenaaddress(pageaddr)
        for i in range(page.nfree):
            freeblockaddr = pageaddr + freeblock
            freeblockptr = llmemory.cast_adr_to_ptr(freeblockaddr,
                                                    FREEBLOCK_PTR)
            freeblock = rffi.getintfield(freeblockptr, 'freeblock')
        assert freeblock != 0
        num_initialized_blocks, rem = divmod(
            freeblock - self.hdrsize, size_class * WORD)
        assert rem == 0, "page size_class misspecified?"
        nblocks = self.nblocks_for_size[size_class]
        return nblocks - num_initialized_blocks


# ____________________________________________________________

class MMapIgnoredFIXED(Exception):
    pass

def _dummy_size(size):
    if we_are_translated():
        return size
    if isinstance(size, int):
        size = llmemory.sizeof(lltype.Char) * size
    return size
