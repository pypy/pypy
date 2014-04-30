/* Imported by rpython/translator/stm/import_stmgc.py */

/* This handles pages of objects outside the nursery.  Every page
   has a "shared copy" and zero or more "private copies".

   The shared copy of a page is stored in the mmap at the file offset
   corresponding to the segment 0 offset.  Initially, accessing a page
   from segment N remaps to segment 0.  If the page is turned private,
   then we "un-remap" it to its initial location.  The 'pages_privatized'
   global array records if a page is currently mapped to segment 0
   (shared page) or to its natural location (private page).

   Note that this page manipulation logic uses remap_file_pages() to
   fully hide its execution cost behind the CPU's memory management unit.
   It should not be confused with the logic of tracking which objects
   are old-and-committed, old-but-modified, overflow objects, and so on
   (which works at the object granularity, not the page granularity).
*/

#define PAGE_FLAG_START   END_NURSERY_PAGE
#define PAGE_FLAG_END     NB_PAGES

struct page_shared_s {
#if NB_SEGMENTS <= 8
    uint8_t by_segment;
#elif NB_SEGMENTS <= 16
    uint16_t by_segment;
#elif NB_SEGMENTS <= 32
    uint32_t by_segment;
#elif NB_SEGMENTS <= 64
    uint64_t by_segment;
#else
#   error "NB_SEGMENTS > 64 not supported right now"
#endif
};

static struct page_shared_s pages_privatized[PAGE_FLAG_END - PAGE_FLAG_START];

static void pages_initialize_shared(uintptr_t pagenum, uintptr_t count);
static void page_privatize(uintptr_t pagenum);
static void page_reshare(uintptr_t pagenum);
static void _page_do_reshare(long segnum, uintptr_t pagenum);
static void pages_setup_readmarkers_for_nursery(void);

static uint64_t increment_total_allocated(ssize_t add_or_remove);
static bool is_major_collection_requested(void);
static void force_major_collection_request(void);
static void reset_major_collection_requested(void);

static inline bool is_private_page(long segnum, uintptr_t pagenum)
{
    assert(pagenum >= PAGE_FLAG_START);
    uint64_t bitmask = 1UL << (segnum - 1);
    return (pages_privatized[pagenum - PAGE_FLAG_START].by_segment & bitmask);
}

static inline void page_check_and_reshare(uintptr_t pagenum)
{
    if (pages_privatized[pagenum - PAGE_FLAG_START].by_segment != 0)
        page_reshare(pagenum);
}
