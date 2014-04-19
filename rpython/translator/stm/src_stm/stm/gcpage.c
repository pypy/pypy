/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


static struct list_s *testing_prebuilt_objs = NULL;
static struct tree_s *tree_prebuilt_objs = NULL;     /* XXX refactor */


static void setup_gcpage(void)
{
    char *base = stm_object_pages + END_NURSERY_PAGE * 4096UL;
    uintptr_t length = (NB_PAGES - END_NURSERY_PAGE) * 4096UL;
    _stm_largemalloc_init_arena(base, length);

    uninitialized_page_start = stm_object_pages + END_NURSERY_PAGE * 4096UL;
    uninitialized_page_stop  = stm_object_pages + NB_PAGES * 4096UL;
}

static void teardown_gcpage(void)
{
    memset(small_alloc, 0, sizeof(small_alloc));
    free_uniform_pages = NULL;
    LIST_FREE(testing_prebuilt_objs);
    if (tree_prebuilt_objs != NULL) {
        tree_free(tree_prebuilt_objs);
        tree_prebuilt_objs = NULL;
    }
}


#define GCPAGE_NUM_PAGES   20

static void setup_N_pages(char *pages_addr, uint64_t num)
{
    pages_initialize_shared((pages_addr - stm_object_pages) / 4096UL, num);
}

static void grab_more_free_pages_for_small_allocations(void)
{
    abort();//XXX
    /* grab N (= GCPAGE_NUM_PAGES) pages out of the top addresses */
    uintptr_t decrease_by = GCPAGE_NUM_PAGES * 4096;
    if (uninitialized_page_stop - uninitialized_page_start <= decrease_by)
        goto out_of_memory;

    uninitialized_page_stop -= decrease_by;

    if (!_stm_largemalloc_resize_arena(uninitialized_page_stop -
                                       uninitialized_page_start))
        goto out_of_memory;

    setup_N_pages(uninitialized_page_start, GCPAGE_NUM_PAGES);

    char *p = uninitialized_page_start;
    long i;
    for (i = 0; i < 16; i++) {
        *(char **)p = free_uniform_pages;
        free_uniform_pages = p;
    }
    return;

 out_of_memory:
    stm_fatalerror("out of memory!");   /* XXX */
}

static char *_allocate_small_slowpath(uint64_t size)
{
    /* not thread-safe!  Use only when holding the mutex */
    assert(_has_mutex());

    if (free_uniform_pages == NULL)
        grab_more_free_pages_for_small_allocations();

    abort();//...
}


static int lock_growth_large = 0;

static char *allocate_outside_nursery_large(uint64_t size)
{
    /* Allocate the object with largemalloc.c from the lower addresses. */
    char *addr = _stm_large_malloc(size);
    if (addr == NULL)
        stm_fatalerror("not enough memory!");

    if (LIKELY(addr + size <= uninitialized_page_start)) {
        return addr;
    }

    /* uncommon case: need to initialize some more pages */
    spinlock_acquire(lock_growth_large);

    if (addr + size > uninitialized_page_start) {
        uintptr_t npages;
        npages = (addr + size - uninitialized_page_start) / 4096UL;
        npages += GCPAGE_NUM_PAGES;
        if (uninitialized_page_stop - uninitialized_page_start <
                npages * 4096UL) {
            stm_fatalerror("out of memory!");   /* XXX */
        }
        setup_N_pages(uninitialized_page_start, npages);
        __sync_synchronize();
        uninitialized_page_start += npages * 4096UL;
    }
    spinlock_release(lock_growth_large);
    return addr;
}

object_t *_stm_allocate_old(ssize_t size_rounded_up)
{
    /* only for tests xxx but stm_setup_prebuilt() uses this now too */
    char *p = allocate_outside_nursery_large(size_rounded_up);
    memset(p, 0, size_rounded_up);

    object_t *o = (object_t *)(p - stm_object_pages);
    o->stm_flags = GCFLAG_WRITE_BARRIER;

    if (testing_prebuilt_objs == NULL)
        testing_prebuilt_objs = list_create();
    LIST_APPEND(testing_prebuilt_objs, o);

    return o;
}


/************************************************************/


static void major_collection_if_requested(void)
{
    assert(!_has_mutex());
    if (!is_major_collection_requested())
        return;

    s_mutex_lock();

    if (is_major_collection_requested()) {   /* if still true */

        int oldstate = change_timing_state(STM_TIME_MAJOR_GC);

        synchronize_all_threads(STOP_OTHERS_UNTIL_MUTEX_UNLOCK);

        if (is_major_collection_requested()) {   /* if *still* true */
            major_collection_now_at_safe_point();
        }

        change_timing_state(oldstate);
    }

    s_mutex_unlock();
}


/************************************************************/


static struct list_s *mark_objects_to_trace;

#define WL_VISITED   255


static inline uintptr_t mark_loc(object_t *obj)
{
    uintptr_t lock_idx = (((uintptr_t)obj) >> 4) - WRITELOCK_START;
    assert(lock_idx < sizeof(write_locks));
    return lock_idx;
}

static inline bool mark_visited_test(object_t *obj)
{
    uintptr_t lock_idx = mark_loc(obj);
    return write_locks[lock_idx] == WL_VISITED;
}

static inline bool mark_visited_test_and_set(object_t *obj)
{
    uintptr_t lock_idx = mark_loc(obj);
    if (write_locks[lock_idx] == WL_VISITED) {
        return true;
    }
    else {
        write_locks[lock_idx] = WL_VISITED;
        return false;
    }
}

static inline bool mark_visited_test_and_clear(object_t *obj)
{
    uintptr_t lock_idx = mark_loc(obj);
    if (write_locks[lock_idx] == WL_VISITED) {
        write_locks[lock_idx] = 0;
        return true;
    }
    else {
        return false;
    }
}

/************************************************************/

static uintptr_t object_last_page(object_t *obj)
{
    uintptr_t lastbyte;
    struct object_s *realobj =
        (struct object_s *)REAL_ADDRESS(stm_object_pages, obj);

    if (realobj->stm_flags & GCFLAG_SMALL_UNIFORM) {
        lastbyte = (uintptr_t)obj;
    }
    else {
        /* get the size of the object */
        size_t obj_size = stmcb_size_rounded_up(realobj);

        /* that's the last byte within the object */
        lastbyte = ((uintptr_t)obj) + obj_size - 1;
    }
    return lastbyte / 4096UL;
}

/* A macro that expands to: run the 'expression' for every page that
   touches objects in the 'modified_old_objects' list.
*/
#define BITOP(expression)                                       \
    LIST_FOREACH_R(                                             \
        get_priv_segment(segment_num)->modified_old_objects,    \
        object_t * /* item */,                                  \
        ({                                                      \
            struct page_shared_s *ps;                           \
            uintptr_t pagenum = ((uintptr_t)item) / 4096UL;     \
            uintptr_t count = object_last_page(item) - pagenum; \
            ps = &pages_privatized[pagenum - PAGE_FLAG_START];  \
            do {                                                \
                expression;                                     \
                ps++;                                           \
            } while (count--);                                  \
        }));

static void major_hide_private_bits_for_modified_objects(long segment_num)
{
    uint64_t negativebitmask = ~(1 << (segment_num - 1));
#ifndef NDEBUG
    BITOP(assert((ps->by_segment & negativebitmask) != ps->by_segment));
#endif
    BITOP(ps->by_segment &= negativebitmask);
}

static void major_restore_private_bits_for_modified_objects(long segment_num)
{
    uint64_t positivebitmask = 1 << (segment_num - 1);
    BITOP(ps->by_segment |= positivebitmask);
}

#undef BITOP

static void major_reshare_pages(void)
{
    /* re-share pages if possible.  Each re-sharing decreases
       total_allocated by 4096. */

    long i;

    for (i = 1; i <= NB_SEGMENTS; i++) {
        /* The 'modified_old_objects' list gives the list of objects
           whose pages need to remain private.  We temporarily remove
           these bits from 'pages_privatized', so that these pages will
           be skipped by the loop below (and by copy_object_to_shared()).
        */
        major_hide_private_bits_for_modified_objects(i);

        /* For each segment, push the current overflow objects from
           private pages to the corresponding shared pages, if
           necessary.  The pages that we will re-share must contain this
           data; otherwise, it would exist only in the private pages,
           and get lost in the loop below.
        */
        struct list_s *lst = get_priv_segment(i)->large_overflow_objects;
        if (lst != NULL) {
            LIST_FOREACH_R(lst, object_t *, copy_object_to_shared(item, i));
        }
    }

    /* Now loop over all pages that are still in 'pages_privatized',
       and re-share them.
     */
    uintptr_t pagenum, endpagenum;
    pagenum = END_NURSERY_PAGE;   /* starts after the nursery */
    endpagenum = (uninitialized_page_start - stm_object_pages) / 4096UL;

    while (1) {
        if (UNLIKELY(pagenum == endpagenum)) {
            /* we reach this point usually twice, because there are
               more pages after 'uninitialized_page_stop' */
            if (endpagenum == NB_PAGES)
                break;   /* done */
            pagenum = (uninitialized_page_stop - stm_object_pages) / 4096UL;
            endpagenum = NB_PAGES;
            continue;
        }

        page_check_and_reshare(pagenum);
        pagenum++;
    }

    /* Done.  Now 'pages_privatized' should be entirely zeroes.  Restore
       the previously-hidden bits
    */
    for (i = 1; i <= NB_SEGMENTS; i++) {
        major_restore_private_bits_for_modified_objects(i);
    }
}


/************************************************************/


static inline void mark_record_trace(object_t **pobj)
{
    /* takes a normal pointer to a thread-local pointer to an object */
    object_t *obj = *pobj;

    /* Note: this obj might be visited already, but from a different
       segment.  We ignore this case and skip re-visiting the object
       anyway.  The idea is that such an object is old (not from the
       current transaction), otherwise it would not be possible to see
       it in two segments; and moreover it is not modified, otherwise
       mark_trace() would have been called on two different segments
       already.  That means that this object is identical in all
       segments and only needs visiting once.  (It may actually be in a
       shared page, or maybe not.)
    */
    if (obj == NULL || mark_visited_test_and_set(obj))
        return;    /* already visited this object */

    LIST_APPEND(mark_objects_to_trace, obj);
}

static void mark_trace(object_t *obj, char *segment_base)
{
    assert(list_is_empty(mark_objects_to_trace));

    while (1) {
        /* trace into the object (the version from 'segment_base') */
        struct object_s *realobj =
            (struct object_s *)REAL_ADDRESS(segment_base, obj);
        stmcb_trace(realobj, &mark_record_trace);

        if (list_is_empty(mark_objects_to_trace))
            break;

        obj = (object_t *)list_pop_item(mark_objects_to_trace);
    }
}

static inline void mark_visit_object(object_t *obj, char *segment_base)
{
    if (obj == NULL || mark_visited_test_and_set(obj))
        return;
    mark_trace(obj, segment_base);
}

static void mark_visit_from_roots(void)
{
    if (testing_prebuilt_objs != NULL) {
        LIST_FOREACH_R(testing_prebuilt_objs, object_t * /*item*/,
                       mark_visit_object(item, stm_object_pages));
    }

    stm_thread_local_t *tl = stm_all_thread_locals;
    do {
        /* If 'tl' is currently running, its 'associated_segment_num'
           field is the segment number that contains the correct
           version of its overflowed objects.  If not, then the
           field is still some correct segment number, and it doesn't
           matter which one we pick. */
        char *segment_base = get_segment_base(tl->associated_segment_num);

        struct stm_shadowentry_s *current = tl->shadowstack;
        struct stm_shadowentry_s *base = tl->shadowstack_base;
        while (current-- != base) {
            if ((((uintptr_t)current->ss) & 3) == 0)
                mark_visit_object(current->ss, segment_base);
        }
        mark_visit_object(tl->thread_local_obj, segment_base);

        tl = tl->next;
    } while (tl != stm_all_thread_locals);

    long i;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        if (get_priv_segment(i)->transaction_state != TS_NONE)
            mark_visit_object(
                get_priv_segment(i)->threadlocal_at_start_of_transaction,
                get_segment_base(i));
    }
}

static void mark_visit_from_modified_objects(void)
{
    /* The modified objects are the ones that may exist in two different
       versions: one in the segment that modified it, and another in all
       other segments.  (It can also be more than two if we don't have
       eager write locking.)
    */
    long i;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        char *base = get_segment_base(i);

        LIST_FOREACH_R(
            get_priv_segment(i)->modified_old_objects,
            object_t * /*item*/,
            ({
                mark_visited_test_and_set(item);
                mark_trace(item, stm_object_pages);  /* shared version */
                mark_trace(item, base);              /* private version */
            }));
    }
}

static void clean_up_segment_lists(void)
{
    long i;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        struct stm_priv_segment_info_s *pseg = get_priv_segment(i);
        struct list_s *lst;

        /* 'objects_pointing_to_nursery' should be empty, but isn't
           necessarily because it also lists objects that have been
           written to but don't actually point to the nursery.  Clear
           it up and set GCFLAG_WRITE_BARRIER again on the objects.
           This is the case for transactions where
               MINOR_NOTHING_TO_DO() == false
           but they still did write-barriers on objects
        */
        lst = pseg->objects_pointing_to_nursery;
        if (lst != NULL) {
            LIST_FOREACH_R(lst, uintptr_t /*item*/,
                ({
                    struct object_s *realobj = (struct object_s *)
                        REAL_ADDRESS(pseg->pub.segment_base, item);
                    assert(!(realobj->stm_flags & GCFLAG_WRITE_BARRIER));
                    realobj->stm_flags |= GCFLAG_WRITE_BARRIER;
                }));
            list_clear(lst);
        }

        /* Remove from 'large_overflow_objects' all objects that die */
        lst = pseg->large_overflow_objects;
        if (lst != NULL) {
            uintptr_t n = list_count(lst);
            while (n > 0) {
                object_t *obj = (object_t *)list_item(lst, --n);
                if (!mark_visited_test(obj)) {
                    list_set_item(lst, n, list_pop_item(lst));
                }
            }
        }
    }
}

static inline bool largemalloc_keep_object_at(char *data)
{
    /* this is called by _stm_largemalloc_sweep() */
    return mark_visited_test_and_clear((object_t *)(data - stm_object_pages));
}

static void sweep_large_objects(void)
{
    _stm_largemalloc_sweep();
}

static void clean_write_locks(void)
{
    /* the write_locks array, containing the visit marker during
       major collection, is cleared in sweep_large_objects() for
       large objects, but is not cleared for small objects.
       Clear it now. */
    object_t *loc2 = (object_t *)(uninitialized_page_stop - stm_object_pages);
    uintptr_t lock2_idx = mark_loc(loc2 - 1) + 1;

    assert_memset_zero(write_locks, lock2_idx);
    memset(write_locks + lock2_idx, 0, sizeof(write_locks) - lock2_idx);
}

static void major_restore_write_locks(void)
{
    /* restore the write locks on the modified objects */
    long i;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        struct stm_priv_segment_info_s *pseg = get_priv_segment(i);

        LIST_FOREACH_R(
            pseg->modified_old_objects,
            object_t * /*item*/,
            ({
                uintptr_t lock_idx = mark_loc(item);
                assert(write_locks[lock_idx] == 0);
                write_locks[lock_idx] = pseg->write_lock_num;
            }));
    }
}

static void major_collection_now_at_safe_point(void)
{
    dprintf(("\n"));
    dprintf((" .----- major collection -----------------------\n"));
    assert(_has_mutex());

    /* first, force a minor collection in each of the other segments */
    major_do_minor_collections();

    dprintf((" | used before collection: %ld\n",
             (long)pages_ctl.total_allocated));

    /* reshare pages */
    if (RESHARE_PAGES)
        major_reshare_pages();

    /* marking */
    LIST_CREATE(mark_objects_to_trace);
    mark_visit_from_modified_objects();
    mark_visit_from_roots();
    LIST_FREE(mark_objects_to_trace);

    /* weakrefs: */
    stm_visit_old_weakrefs();

    /* cleanup */
    clean_up_segment_lists();

    /* sweeping */
    sweep_large_objects();
    //sweep_uniform_pages();

    clean_write_locks();
    major_restore_write_locks();

    dprintf((" | used after collection:  %ld\n",
             (long)pages_ctl.total_allocated));
    dprintf((" `----------------------------------------------\n"));

    reset_major_collection_requested();
}
