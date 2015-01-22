/* Imported by rpython/translator/stm/import_stmgc.py */
/*
  We have logical pages: one %gs relative pointer can point in some
      logical page
  We have virtual pages: one virtual address can point in some
      virtual page. We have NB_SEGMENTS virtual pages per logical page.

  Each virtual page is either accessible, or PAGE_NO_ACCESS (and then
  has no underlying memory).

  TODO: one way to save memory is to re-share pages during major GC.
  The pages are mapped MAP_PRIVATE in all segments. We could use an
  extra segment that is mapped SHARED to underlying file pages so
  we can map PRIVATE pages from segments to it. The idea is that
  a major GC first validates all segments (incl. the extra seg.),
  then re-maps all PRIVATE, unmodified pages to the SHARED (unmodified)
  page. Thus, we get "free" copy-on-write supported by the kernel.
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

enum {
    PAGE_NO_ACCESS = 0,
    PAGE_ACCESSIBLE = 1
};

static struct page_shared_s pages_status[PAGE_FLAG_END - PAGE_FLAG_START];

static void page_mark_accessible(long segnum, uintptr_t pagenum);
static void page_mark_inaccessible(long segnum, uintptr_t pagenum);

static uint64_t increment_total_allocated(ssize_t add_or_remove);
static bool is_major_collection_requested(void);
static void force_major_collection_request(void);
static void reset_major_collection_requested(void);


static inline char *get_virtual_page(long segnum, uintptr_t pagenum)
{
    /* logical page -> virtual page */
    return get_segment_base(segnum) + pagenum * 4096;
}

static inline char *get_virtual_address(long segnum, object_t *obj)
{
    return REAL_ADDRESS(get_segment_base(segnum), obj);
}

static inline bool get_page_status_in(long segnum, uintptr_t pagenum)
{
    /* reading page status requires "read"-lock: */
    assert(STM_PSEGMENT->privatization_lock);

    OPT_ASSERT(segnum < 8 * sizeof(struct page_shared_s));
    volatile struct page_shared_s *ps = (volatile struct page_shared_s *)
        &pages_status[pagenum - PAGE_FLAG_START];

    return (ps->by_segment >> segnum) & 1;
}

static inline void set_page_status_in(long segnum, uintptr_t pagenum,
                                      bool status)
{
    /* writing page status requires "write"-lock: */
    assert(all_privatization_locks_acquired());

    OPT_ASSERT(segnum < 8 * sizeof(struct page_shared_s));
    volatile struct page_shared_s *ps = (volatile struct page_shared_s *)
        &pages_status[pagenum - PAGE_FLAG_START];

    assert(status != get_page_status_in(segnum, pagenum));
    __sync_fetch_and_xor(&ps->by_segment, 1UL << segnum); /* invert the flag */
}
