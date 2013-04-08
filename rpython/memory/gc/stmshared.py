from rpython.rtyper.lltypesystem import lltype, llmemory, llarena, rffi
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rlib.objectmodel import free_non_gc_object, we_are_translated
from rpython.rlib.debug import ll_assert, fatalerror
from rpython.rlib import rthread

WORD = LONG_BIT // 8
NULL = llmemory.NULL
WORD_POWER_2 = {32: 2, 64: 3}[LONG_BIT]
assert 1 << WORD_POWER_2 == WORD

# Linux's glibc is good at 'malloc(1023*WORD)': the blocks ("pages") it
# returns are exactly 1024 words apart, reserving only one extra word
# for its internal data
TRANSLATED_PAGE_SIZE = 1023 * WORD

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
    # -- The following pointer makes a chained list of pages.  For non-full
    #    pages, it is a chained list of pages having the same size class,
    #    rooted in 'page_for_size[size_class]'.  For full pages, it is a
    #    different chained list rooted in 'full_page_for_size[size_class]'.
    ('nextpage', PAGE_PTR),
    # -- The number of free blocks.  The numbers of uninitialized and
    #    allocated blocks can be deduced from the context if needed.
    ('nfree', lltype.Signed),
    # -- The chained list of free blocks.  It ends as a pointer to the
    #    first uninitialized block (pointing to data that is uninitialized,
    #    or to the end of the page).
    ('freeblock', llmemory.Address),
    # -- The structure above is 3 words, which is a good value:
    #    '(1023-3) % N' is zero or very small for various small N's,
    #    i.e. there is not much wasted space.
    )
PAGE_PTR.TO.become(PAGE_HEADER)
PAGE_NULL = lltype.nullptr(PAGE_HEADER)

# ------------------------------------------------------------


class StmGCSharedArea(object):
    _alloc_flavor_ = 'raw'

    def __init__(self, gc, page_size, small_request_threshold):
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
        self.low_usage_page = lltype.malloc(rffi.CArray(PAGE_PTR), length,
                                            flavor='raw', zero=True,
                                            immortal=True)
        self.nblocks_for_size = lltype.malloc(rffi.CArray(lltype.Signed),
                                              length, flavor='raw',
                                              immortal=True)
        self.hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))
        self.nblocks_for_size[0] = 0    # unused
        for i in range(1, length):
            self.nblocks_for_size[i] = (page_size - self.hdrsize) // (WORD * i)
        assert self.nblocks_for_size[length-1] >= 1

    def setup(self):
        self.ll_low_usage_lock = rthread.allocate_ll_lock()


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
        self.chained_list = NULL
        #
        # These two arrays contain each 'length' chained lists of pages.
        # For each size N between WORD and 'small_request_threshold'
        # (included), the corresponding chained list contains pages
        # which store objects of size N.  The 'page_for_size' lists are
        # for pages which still have room for at least one more object,
        # and the 'full_page_for_size' lists are for full pages.
        length = sharedarea.small_request_threshold / WORD + 1
        self.page_for_size = lltype.malloc(rffi.CArray(PAGE_PTR), length,
                                           flavor='raw', zero=True,
                                           immortal=True)
        self.full_page_for_size = lltype.malloc(rffi.CArray(PAGE_PTR), length,
                                                flavor='raw', zero=True,
                                                immortal=True)
        #
        if not we_are_translated():
            self._seen_pages = set()

    def _malloc_size_class(self, size_class):
        """Malloc one object of the given size_class (== number of WORDs)."""
        ll_assert(size_class > 0, "malloc_size_class: null or neg size_class")
        ll_assert(size_class <= self.sharedarea.small_request_threshold,
                  "malloc_size_class: too big")
        #
        # Get the page to use
        page = self.page_for_size[size_class]
        if page == PAGE_NULL:
            page = self._allocate_new_page(size_class)
        #
        # The result is simply 'page.freeblock'
        result = page.freeblock
        nsize = size_class << WORD_POWER_2
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
        if freeblock - pageaddr > self.sharedarea.page_size - nsize:
            # This was the last free block, so unlink the page from the
            # chained list and put it in the 'full_page_for_size' list.
            self.page_for_size[size_class] = page.nextpage
            page.nextpage = self.full_page_for_size[size_class]
            self.full_page_for_size[size_class] = page
        #
        return result


    def _allocate_new_page(self, size_class):
        """Allocate and return a new page for the given size_class."""
        #
        # If 'low_usage_page' has pages ready, return one of them.
        # Check both before acquiring the lock (NULL is the common case
        # and getting it occasionally wrong is not a problem), and after.
        result = NULL
        sharedarea = self.sharedarea
        if sharedarea.low_usage_page[size_class] != PAGE_NULL:
            XXX   # self.ll_low_usage_lock...
        #
        # If unsuccessful, just raw-malloc a new page.
        if not result:
            result = llarena.arena_malloc(sharedarea.page_size, 0)
            if not result:
                fatalerror("FIXME: Out of memory! (should raise MemoryError)")
                return PAGE_NULL
            if not we_are_translated():
                self._seen_pages.add(result)
            llarena.arena_reserve(result, llmemory.sizeof(PAGE_HEADER))
        #
        # Initialize the fields of the resulting page
        page = llmemory.cast_adr_to_ptr(result, PAGE_PTR)
        page.nfree = 0
        page.freeblock = result + sharedarea.hdrsize
        page.nextpage = PAGE_NULL
        ll_assert(self.page_for_size[size_class] == PAGE_NULL,
                  "allocate_new_page() called but a page is already waiting")
        self.page_for_size[size_class] = page
        return page


    def malloc_object(self, totalsize):
        """Malloc.  You should also call add_regular() later, or keep it in
        some other data structure.  Note that it is not zero-filled."""
        nsize = llmemory.raw_malloc_usage(totalsize)
        if nsize <= self.sharedarea.small_request_threshold:
            size_class = (nsize + WORD_POWER_2 - 1) >> WORD_POWER_2
            result = self._malloc_size_class(size_class)
            llarena.arena_reserve(result, _dummy_size(totalsize))
            return result
        else:
            XXX
            #llarena.arena_malloc(llmemory.raw_malloc_usage(totalsize), 0)

    def add_regular(self, obj):
        """After malloc_object(), register the object in the internal chained
        list.  For objects whose 'revision' field is not otherwise needed."""
        self.gc.set_obj_revision(obj, self.chained_list)
        self.chained_list = obj

    def free_object(self, adr2):
        adr1 = adr2 - self.gc.gcheaderbuilder.size_gc_header
        llarena.arena_free(llarena.getfakearenaaddress(adr1))

    def free_and_clear(self):
        obj = self.chained_list
        self.chained_list = NULL
        while obj:
            next = self.gc.obj_revision(obj)
            self.free_object(obj)
            obj = next

    def free_and_clear_list(self, lst):
        while lst.non_empty():
            self.free_object(lst.pop())

    def delete(self):
        free_non_gc_object(self)


# ____________________________________________________________

def _dummy_size(size):
    if we_are_translated():
        return size
    if isinstance(size, int):
        size = llmemory.sizeof(lltype.Char) * size
    return size
