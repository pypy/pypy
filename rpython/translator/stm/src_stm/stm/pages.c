/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


/************************************************************/

static union {
    struct {
        uint8_t mutex_pages;
        volatile bool major_collection_requested;
        uint64_t total_allocated;  /* keep track of how much memory we're
                                      using, ignoring nurseries */
        uint64_t total_allocated_bound;
    };
    char reserved[64];
} pages_ctl __attribute__((aligned(64)));


static void setup_pages(void)
{
    pages_ctl.total_allocated_bound = GC_MIN;
}

static void teardown_pages(void)
{
    memset(&pages_ctl, 0, sizeof(pages_ctl));
    memset(pages_privatized, 0, sizeof(pages_privatized));
}

static void mutex_pages_lock(void)
{
    if (__sync_lock_test_and_set(&pages_ctl.mutex_pages, 1) == 0)
        return;

    int previous = change_timing_state(STM_TIME_SPIN_LOOP);
    while (__sync_lock_test_and_set(&pages_ctl.mutex_pages, 1) != 0) {
        spin_loop();
    }
    change_timing_state(previous);
}

static void mutex_pages_unlock(void)
{
    __sync_lock_release(&pages_ctl.mutex_pages);
}

static bool _has_mutex_pages(void)
{
    return pages_ctl.mutex_pages != 0;
}

static uint64_t increment_total_allocated(ssize_t add_or_remove)
{
    assert(_has_mutex_pages());
    pages_ctl.total_allocated += add_or_remove;

    if (pages_ctl.total_allocated >= pages_ctl.total_allocated_bound)
        pages_ctl.major_collection_requested = true;

    return pages_ctl.total_allocated;
}

static bool is_major_collection_requested(void)
{
    return pages_ctl.major_collection_requested;
}

static void force_major_collection_request(void)
{
    pages_ctl.major_collection_requested = true;
}

static void reset_major_collection_requested(void)
{
    assert(_has_mutex());

    uint64_t next_bound = (uint64_t)((double)pages_ctl.total_allocated *
                                     GC_MAJOR_COLLECT);
    if (next_bound < GC_MIN)
        next_bound = GC_MIN;

    pages_ctl.total_allocated_bound = next_bound;
    pages_ctl.major_collection_requested = false;
}

/************************************************************/


static void d_remap_file_pages(char *addr, size_t size, ssize_t pgoff)
{
    dprintf(("remap_file_pages: 0x%lx bytes: (seg%ld %p) --> (seg%ld %p)\n",
             (long)size,
             (long)((addr - stm_object_pages) / 4096UL) / NB_PAGES,
             (void *)((addr - stm_object_pages) % (4096UL * NB_PAGES)),
             (long)pgoff / NB_PAGES,
             (void *)((pgoff % NB_PAGES) * 4096UL)));
    assert(size % 4096 == 0);
    assert(size <= TOTAL_MEMORY);
    assert(((uintptr_t)addr) % 4096 == 0);
    assert(addr >= stm_object_pages);
    assert(addr <= stm_object_pages + TOTAL_MEMORY - size);
    assert(pgoff >= 0);
    assert(pgoff <= (TOTAL_MEMORY - size) / 4096UL);

    /* assert remappings follow the rule that page N in one segment
       can only be remapped to page N in another segment */
    assert(((addr - stm_object_pages) / 4096UL - pgoff) % NB_PAGES == 0);

    int res = remap_file_pages(addr, size, 0, pgoff, 0);
    if (UNLIKELY(res < 0))
        stm_fatalerror("remap_file_pages: %m");
}

static void pages_initialize_shared(uintptr_t pagenum, uintptr_t count)
{
    /* call remap_file_pages() to make all pages in the range(pagenum,
       pagenum+count) refer to the same physical range of pages from
       segment 0. */
    uintptr_t i;
    assert(_has_mutex_pages());
    if (count == 0)
        return;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        char *segment_base = get_segment_base(i);
        d_remap_file_pages(segment_base + pagenum * 4096UL,
                           count * 4096UL, pagenum);
    }
}

static void page_privatize(uintptr_t pagenum)
{
    if (is_private_page(STM_SEGMENT->segment_num, pagenum)) {
        /* the page is already privatized */
        return;
    }

    /* lock, to prevent concurrent threads from looking up this thread's
       'pages_privatized' bits in parallel */
    mutex_pages_lock();

    /* "unmaps" the page to make the address space location correspond
       again to its underlying file offset (XXX later we should again
       attempt to group together many calls to d_remap_file_pages() in
       succession) */
    uintptr_t pagenum_in_file = NB_PAGES * STM_SEGMENT->segment_num + pagenum;
    char *new_page = stm_object_pages + pagenum_in_file * 4096UL;
    d_remap_file_pages(new_page, 4096, pagenum_in_file);
    increment_total_allocated(4096);

    /* copy the content from the shared (segment 0) source */
    pagecopy(new_page, stm_object_pages + pagenum * 4096UL);

    /* add this thread's 'pages_privatized' bit */
    uint64_t bitmask = 1UL << (STM_SEGMENT->segment_num - 1);
    pages_privatized[pagenum - PAGE_FLAG_START].by_segment |= bitmask;

    mutex_pages_unlock();
}

static void _page_do_reshare(long segnum, uintptr_t pagenum)
{
    char *segment_base = get_segment_base(segnum);
    d_remap_file_pages(segment_base + pagenum * 4096UL,
                       4096, pagenum);
}

static void page_reshare(uintptr_t pagenum)
{
    struct page_shared_s ps = pages_privatized[pagenum - PAGE_FLAG_START];
    pages_privatized[pagenum - PAGE_FLAG_START].by_segment = 0;

    long j, total = 0;
    for (j = 0; j < NB_SEGMENTS; j++) {
        if (ps.by_segment & (1 << j)) {
            /* Page 'pagenum' is private in segment 'j + 1'. Reshare */
            char *segment_base = get_segment_base(j + 1);

            madvise(segment_base + pagenum * 4096UL, 4096, MADV_DONTNEED);
            d_remap_file_pages(segment_base + pagenum * 4096UL,
                               4096, pagenum);
            total -= 4096;
        }
    }
    increment_total_allocated(total);
}

static void pages_setup_readmarkers_for_nursery(void)
{
    /* The nursery page's read markers are never read, but must still
       be writeable.  We'd like to map the pages to a general "trash
       page"; missing one, we remap all the pages over to the same one.
       We still keep one page *per segment* to avoid cross-CPU cache
       conflicts.

       (XXX no performance difference measured so far)
    */
    long i, j;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        char *segment_base = get_segment_base(i);

        for (j = FIRST_READMARKER_PAGE + 1; j < FIRST_OLD_RM_PAGE; j++) {
            remap_file_pages(segment_base + 4096 * j, 4096, 0,
                             i * NB_PAGES + FIRST_READMARKER_PAGE, 0);
            /* errors here ignored */
        }
    }
}
