/* Imported by rpython/translator/stm/import_stmgc.py */

enum /* flag_page_private */ {
    /* The page is not in use.  Assume that each segment sees its own copy. */
    FREE_PAGE=0,

    /* The page is shared by all segments.  Each segment sees the same
       physical page (the one that is within the segment 0 mmap address). */
    SHARED_PAGE,

    /* For only one range of pages at a time, around the call to
       remap_file_pages() that un-shares the pages (SHARED -> PRIVATE). */
    REMAPPING_PAGE,

    /* Page is private for each segment. */
    PRIVATE_PAGE,

    /* gcpage.c: page contains objects that have been traced in the
       segment > 0 */
    SEGMENT1_PAGE,
};

static uint8_t flag_page_private[NB_PAGES];

static void _pages_privatize(uintptr_t pagenum, uintptr_t count, bool full);
static void pages_initialize_shared(uintptr_t pagenum, uintptr_t count);
//static void pages_make_shared_again(uintptr_t pagenum, uintptr_t count);

static void mutex_pages_lock(void);
static void mutex_pages_unlock(void);
static uint64_t increment_total_allocated(ssize_t add_or_remove);
static bool is_major_collection_requested(void);
static void force_major_collection_request(void);
static void reset_major_collection_requested(void);

inline static void pages_privatize(uintptr_t pagenum, uintptr_t count,
                                   bool full) {
    /* This is written a bit carefully so that a call with a constant
       count == 1 will turn this loop into just one "if". */
    while (flag_page_private[pagenum] == PRIVATE_PAGE) {
        if (!--count) {
            return;
        }
        pagenum++;
    }
    _pages_privatize(pagenum, count, full);
}

/* static bool is_fully_in_shared_pages(object_t *obj); */
