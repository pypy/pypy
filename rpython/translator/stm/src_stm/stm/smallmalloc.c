/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif

#define PAGE_SMSIZE_START   0
#define PAGE_SMSIZE_END     NB_SHARED_PAGES

typedef struct {
    uint8_t sz;
} full_page_size_t;

static full_page_size_t full_pages_object_size[PAGE_SMSIZE_END - PAGE_SMSIZE_START];
/* ^^^ This array contains the size (in number of words) of the objects
   in the given page, provided it's a "full page of small objects".  It
   is 0 if it's not such a page, if it's fully free, or if it's in
   small_page_lists.  It is not 0 as soon as the page enters the
   segment's 'small_malloc_data.loc_free' (even if the page is not
   technically full yet, it will be very soon in this case).
*/

static full_page_size_t *get_full_page_size(char *smallpage)
{
    uintptr_t pagenum = (((char *)smallpage) - END_NURSERY_PAGE * 4096UL - stm_object_pages) / 4096;
    /* <= PAGE_SMSIZE_END because we may ask for it when there is no
       page with smallobjs yet and uninit_page_stop == NB_PAGES... */
    assert(PAGE_SMSIZE_START <= pagenum && pagenum <= PAGE_SMSIZE_END);
    return &full_pages_object_size[pagenum - PAGE_SMSIZE_START];
}


#ifdef STM_TESTS
bool (*_stm_smallmalloc_keep)(char *data);   /* a hook for tests */
#endif

static void teardown_smallmalloc(void)
{
    memset(small_page_lists, 0, sizeof(small_page_lists));
    assert(free_uniform_pages == NULL);   /* done by the previous line */
    first_small_uniform_loc = (uintptr_t) -1;
#ifdef STM_TESTS
    _stm_smallmalloc_keep = NULL;
#endif
    memset(full_pages_object_size, 0, sizeof(full_pages_object_size));
}

static uint8_t gmfp_lock = 0;

static void grab_more_free_pages_for_small_allocations(void)
{
    dprintf(("grab_more_free_pages_for_small_allocation()\n"));
    /* Grab GCPAGE_NUM_PAGES pages out of the top addresses.  Use the
       lock of pages.c to prevent any remapping from occurring under our
       feet.
    */
    stm_spinlock_acquire(gmfp_lock);

    if (free_uniform_pages == NULL) {

        uintptr_t decrease_by = GCPAGE_NUM_PAGES * 4096;
        if (uninitialized_page_stop - uninitialized_page_start < decrease_by)
            goto out_of_memory;

        uninitialized_page_stop -= decrease_by;
        first_small_uniform_loc = uninitialized_page_stop - stm_object_pages;

        char *base = stm_object_pages + END_NURSERY_PAGE * 4096UL;
        if (!_stm_largemalloc_resize_arena(uninitialized_page_stop - base))
            goto out_of_memory;

        /* make writable in sharing seg */
        setup_N_pages(uninitialized_page_stop, GCPAGE_NUM_PAGES);

        char *p = uninitialized_page_stop;
        long i;
        for (i = 0; i < GCPAGE_NUM_PAGES; i++) {
            /* add to free_uniform_pages list */
            struct small_free_loc_s *to_add = (struct small_free_loc_s *)p;

        retry:
            to_add->nextpage = free_uniform_pages;
            if (UNLIKELY(!__sync_bool_compare_and_swap(
                             &free_uniform_pages,
                             to_add->nextpage,
                             to_add))) {
                goto retry;
            }

            p += 4096;
        }
    }

    stm_spinlock_release(gmfp_lock);
    return;

 out_of_memory:
    stm_fatalerror("out of memory!\n");   /* XXX */
}

static char *_allocate_small_slowpath(uint64_t size)
{
    dprintf(("_allocate_small_slowpath(%lu)\n", size));
    long n = size / 8;
    struct small_free_loc_s *smallpage;
    struct small_free_loc_s *TLPREFIX *fl =
        &STM_PSEGMENT->small_malloc_data.loc_free[n];
    assert(*fl == NULL);

 retry:
    /* First try to grab the next page from the global 'small_page_list'
     */
    smallpage = small_page_lists[n];
    if (smallpage != NULL) {
        if (UNLIKELY(!__sync_bool_compare_and_swap(&small_page_lists[n],
                                                   smallpage,
                                                   smallpage->nextpage)))
            goto retry;

        /* Succeeded: we have a page in 'smallpage' */
        *fl = smallpage->next;
        get_full_page_size((char *)smallpage)->sz = n;
        return (char *)smallpage;
    }

    /* There is no more page waiting for the correct size of objects.
       Maybe we can pick one from free_uniform_pages.
     */
    smallpage = free_uniform_pages;
    if (LIKELY(smallpage != NULL)) {
        if (UNLIKELY(!__sync_bool_compare_and_swap(&free_uniform_pages,
                                                   smallpage,
                                                   smallpage->nextpage)))
            goto retry;

        /* got a new page: */
        increment_total_allocated(4096);

        /* Succeeded: we have a page in 'smallpage', which is not
           initialized so far, apart from the 'nextpage' field read
           above.  Initialize it.
        */
        struct small_free_loc_s *p, **previous;
        assert(!(((uintptr_t)smallpage) & 4095));
        previous = (struct small_free_loc_s **)
            REAL_ADDRESS(STM_SEGMENT->segment_base, fl);

        /* Initialize all slots from the second one to the last one to
           contain a chained list */
        uintptr_t i = size;
        while (i <= 4096 - size) {
            p = (struct small_free_loc_s *)(((char *)smallpage) + i);
            *previous = p;
            previous = &p->next;
            i += size;
        }
        *previous = NULL;

        /* The first slot is immediately returned */
        get_full_page_size((char *)smallpage)->sz = n;
        return (char *)smallpage;
    }

    /* Not a single free page left.  Grab some more free pages and retry.
     */
    grab_more_free_pages_for_small_allocations();
    goto retry;
}

__attribute__((always_inline))
static inline stm_char *allocate_outside_nursery_small(uint64_t size)
{
    OPT_ASSERT((size & 7) == 0);
    OPT_ASSERT(16 <= size && size <= GC_LAST_SMALL_SIZE);

    struct small_free_loc_s *TLPREFIX *fl =
        &STM_PSEGMENT->small_malloc_data.loc_free[size / 8];

    struct small_free_loc_s *result = *fl;

    if (UNLIKELY(result == NULL)) {
        char *addr = _allocate_small_slowpath(size);
        ((struct object_s*)addr)->stm_flags = 0;
        return (stm_char*)
            (addr - stm_object_pages);
    }

    *fl = result->next;
    /* dprintf(("allocate_outside_nursery_small(%lu): %p\n", */
    /*          size, (char*)((char *)result - stm_object_pages))); */
    ((struct object_s*)result)->stm_flags = 0;
    return (stm_char*)
        ((char *)result - stm_object_pages);
}

object_t *_stm_allocate_old_small(ssize_t size_rounded_up)
{
    stm_char *p = allocate_outside_nursery_small(size_rounded_up);
    object_t *o = (object_t *)p;

    // sharing seg0 needs to be current:
    assert(STM_SEGMENT->segment_num == 0);
    memset(REAL_ADDRESS(STM_SEGMENT->segment_base, o), 0, size_rounded_up);
    o->stm_flags = GCFLAG_WRITE_BARRIER;

    if (testing_prebuilt_objs == NULL)
        testing_prebuilt_objs = list_create();
    LIST_APPEND(testing_prebuilt_objs, o);

    dprintf(("_stm_allocate_old_small(%lu): %p, seg=%d, page=%lu\n",
             size_rounded_up, p,
             get_segment_of_linear_address(stm_object_pages + (uintptr_t)p),
             (uintptr_t)p / 4096UL));

    return o;
}


/************************************************************/

static inline bool _smallmalloc_sweep_keep(char *p)
{
#ifdef STM_TESTS
    if (_stm_smallmalloc_keep != NULL) {
        // test wants a TLPREFIXd address
        return _stm_smallmalloc_keep((char*)(p - stm_object_pages));
    }
#endif
    return smallmalloc_keep_object_at(p);
}

void check_order_inside_small_page(struct small_free_loc_s *page)
{
#ifndef NDEBUG
    /* the free locations are supposed to be in increasing order */
    while (page->next != NULL) {
        assert(page->next > page);
        page = page->next;
    }
#endif
}

static char *getbaseptr(struct small_free_loc_s *fl)
{
    return (char *)(((uintptr_t)fl) & ~4095);
}

void sweep_small_page(char *baseptr, struct small_free_loc_s *page_free,
                      long szword)
{
    if (page_free != NULL)
        check_order_inside_small_page(page_free);

    /* for every non-free location, ask if we must free it */
    uintptr_t i, size = szword * 8;
    bool any_object_remaining = false, any_object_dying = false;
    struct small_free_loc_s *fl = page_free;
    struct small_free_loc_s *flprev = NULL;

    /* XXX could optimize for the case where all objects die: we don't
       need to painfully rebuild the free list in the whole page, just
       to have it ignored in the end because we put the page into
       'free_uniform_pages' */

    for (i = 0; i <= 4096 - size; i += size) {
        char *p = baseptr + i;
        if (p == (char *)fl) {
            /* location is already free */
            flprev = fl;
            fl = fl->next;
            any_object_dying = true;
        }
        else if (!_smallmalloc_sweep_keep(p)) {
            /* the location should be freed now */
#ifdef STM_TESTS
            /* fill location with 0xdd in all segs except seg0 */
            int j;
            object_t *obj = (object_t*)(p - stm_object_pages);
            uintptr_t page = (baseptr - stm_object_pages) / 4096UL;
            for (j = 1; j < NB_SEGMENTS; j++)
                if (get_page_status_in(j, page) == PAGE_ACCESSIBLE)
                    memset(get_virtual_address(j, obj), 0xdd, szword*8);
#endif
            //dprintf(("free small %p : %lu\n", (char*)(p - stm_object_pages), szword*8));

            if (flprev == NULL) {
                flprev = (struct small_free_loc_s *)p;
                flprev->next = fl;
                page_free = flprev;
            }
            else {
                assert(flprev->next == fl);
                flprev->next = (struct small_free_loc_s *)p;
                flprev = (struct small_free_loc_s *)p;
                flprev->next = fl;
            }
            any_object_dying = true;
        }
        else {
            //dprintf(("keep small %p : %lu\n", (char*)(p - stm_object_pages), szword*8));
            any_object_remaining = true;
        }
    }

    if (!any_object_remaining) {
        /* give page back to free_uniform_pages and thus make it
           inaccessible from all other segments again (except seg0) */
        uintptr_t page = (baseptr - stm_object_pages) / 4096UL;
        for (i = 1; i < NB_SEGMENTS; i++) {
            if (get_page_status_in(i, page) == PAGE_ACCESSIBLE)
                page_mark_inaccessible(i, page);
        }

        ((struct small_free_loc_s *)baseptr)->nextpage = free_uniform_pages;
        free_uniform_pages = (struct small_free_loc_s *)baseptr;

        /* gave the page back */
        increment_total_allocated(-4096);
    }
    else if (!any_object_dying) {
        /* this is still a full page. only in this case we set the
           full_page_size again: */
        get_full_page_size(baseptr)->sz = szword;
    }
    else {
        check_order_inside_small_page(page_free);
        page_free->nextpage = small_page_lists[szword];
        small_page_lists[szword] = page_free;
    }
}

void _stm_smallmalloc_sweep(void)
{
    long i, szword;
    for (szword = 2; szword < GC_N_SMALL_REQUESTS; szword++) {
        struct small_free_loc_s *page = small_page_lists[szword];
        struct small_free_loc_s *nextpage;
        small_page_lists[szword] = NULL;

        /* process the pages that the various segments are busy filling */
        /* including sharing seg0 for old-malloced things */
        for (i = 0; i < NB_SEGMENTS; i++) {
            struct stm_priv_segment_info_s *pseg = get_priv_segment(i);
            struct small_free_loc_s **fl =
                    &pseg->small_malloc_data.loc_free[szword];
            if (*fl != NULL) {
                /* the entry in full_pages_object_size[] should already be
                   szword.  We reset it to 0. */
                full_page_size_t *full_page_size = get_full_page_size((char *)*fl);
                assert(full_page_size->sz == szword);
                full_page_size->sz = 0;
                sweep_small_page(getbaseptr(*fl), *fl, szword);
                *fl = NULL;
            }
        }

        /* process all the other partially-filled pages */
        while (page != NULL) {
            /* for every page in small_page_lists: assert that the
               corresponding full_pages_object_size[] entry is 0 */
            assert(get_full_page_size((char *)page)->sz == 0);
            nextpage = page->nextpage;
            sweep_small_page(getbaseptr(page), page, szword);
            page = nextpage;
        }
    }

    /* process the really full pages, which are the ones which still
       have a non-zero full_pages_object_size[] entry */
    char *pageptr = uninitialized_page_stop;
    full_page_size_t *fpsz_start = get_full_page_size(pageptr);
    full_page_size_t *fpsz_end = &full_pages_object_size[PAGE_SMSIZE_END -
                                                         PAGE_SMSIZE_START];
    full_page_size_t *fpsz;
    for (fpsz = fpsz_start; fpsz < fpsz_end; fpsz++, pageptr += 4096) {
        uint8_t sz = fpsz->sz;
        if (sz != 0) {
            fpsz->sz = 0;
            sweep_small_page(pageptr, NULL, sz);
        }
    }
}
