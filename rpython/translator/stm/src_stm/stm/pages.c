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
}

static void mutex_pages_lock(void)
{
    while (__sync_lock_test_and_set(&pages_ctl.mutex_pages, 1) != 0) {
        spin_loop();
    }
}

static void mutex_pages_unlock(void)
{
    __sync_lock_release(&pages_ctl.mutex_pages);
}

__attribute__((unused))
static bool _has_mutex_pages(void)
{
    return pages_ctl.mutex_pages != 0;
}

static uint64_t increment_total_allocated(ssize_t add_or_remove)
{
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

    int res = remap_file_pages(addr, size, 0, pgoff, 0);
    if (UNLIKELY(res < 0))
        stm_fatalerror("remap_file_pages: %m\n");
}

static void pages_initialize_shared(uintptr_t pagenum, uintptr_t count)
{
    /* call remap_file_pages() to make all pages in the range(pagenum,
       pagenum+count) refer to the same physical range of pages from
       segment 0. */
    uintptr_t i;
    assert(_has_mutex_pages());
    for (i = 1; i < NB_SEGMENTS; i++) {
        char *segment_base = get_segment_base(i);
        d_remap_file_pages(segment_base + pagenum * 4096UL,
                           count * 4096UL, pagenum);
    }
    for (i = 0; i < count; i++)
        flag_page_private[pagenum + i] = SHARED_PAGE;
}

#if 0
static void pages_make_shared_again(uintptr_t pagenum, uintptr_t count)
{
    /* Same as pages_initialize_shared(), but tries hard to minimize the
       total number of pages that remap_file_pages() must handle, by
       fragmenting calls as much as possible (the overhead of one system
       call appears smaller as the overhead per page). */
    uintptr_t start, i = 0;
    while (i < count) {
        if (flag_page_private[pagenum + (i++)] == SHARED_PAGE)
            continue;
        start = i;    /* first index of a private page */
        while (1) {
            i++;
            if (i == count || flag_page_private[pagenum + i] == SHARED_PAGE)
                break;
        }
        pages_initialize_shared(pagenum + start, i - start);
    }
}
#endif

static void privatize_range(uintptr_t pagenum, uintptr_t count, bool full)
{
    ssize_t pgoff1 = pagenum;
    ssize_t pgoff2 = pagenum + NB_PAGES;
    ssize_t localpgoff = pgoff1 + NB_PAGES * STM_SEGMENT->segment_num;
    ssize_t otherpgoff = pgoff1 + NB_PAGES * (1 - STM_SEGMENT->segment_num);

    void *localpg = stm_object_pages + localpgoff * 4096UL;
    void *otherpg = stm_object_pages + otherpgoff * 4096UL;

    memset(flag_page_private + pagenum, REMAPPING_PAGE, count);
    d_remap_file_pages(localpg, count * 4096, pgoff2);
    uintptr_t i;
    if (full) {
        for (i = 0; i < count; i++) {
            pagecopy(localpg + 4096 * i, otherpg + 4096 * i);
        }
    }
    else {
        pagecopy(localpg, otherpg);
        if (count > 1)
            pagecopy(localpg + 4096 * (count-1), otherpg + 4096 * (count-1));
    }
    write_fence();
    memset(flag_page_private + pagenum, PRIVATE_PAGE, count);
    increment_total_allocated(4096 * count);
}

static void _pages_privatize(uintptr_t pagenum, uintptr_t count, bool full)
{
    /* narrow the range of pages to privatize from the end: */
    while (flag_page_private[pagenum + count - 1] == PRIVATE_PAGE) {
        if (!--count)
            return;
    }

    mutex_pages_lock();

    uintptr_t page_start_range = pagenum;
    uintptr_t pagestop = pagenum + count;

    for (; pagenum < pagestop; pagenum++) {
        uint8_t prev = flag_page_private[pagenum];
        if (prev == PRIVATE_PAGE) {
            if (pagenum > page_start_range) {
                privatize_range(page_start_range,
                                pagenum - page_start_range, full);
            }
            page_start_range = pagenum + 1;
        }
        else {
            assert(prev == SHARED_PAGE);
        }
    }

    if (pagenum > page_start_range) {
        privatize_range(page_start_range,
                        pagenum - page_start_range, full);
    }

    mutex_pages_unlock();
}

#if 0
static bool is_fully_in_shared_pages(object_t *obj)
{
    uintptr_t first_page = ((uintptr_t)obj) / 4096UL;

    if ((obj->stm_flags & GCFLAG_SMALL_UNIFORM) != 0)
        return (flag_page_private[first_page] == SHARED_PAGE);

    ssize_t obj_size = stmcb_size_rounded_up(
        (struct object_s *)REAL_ADDRESS(stm_object_pages, obj));

    uintptr_t last_page = (((uintptr_t)obj) + obj_size - 1) / 4096UL;

    do {
        if (flag_page_private[first_page++] != SHARED_PAGE)
            return false;
    } while (first_page <= last_page);

    return true;
}
#endif
