/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif
static struct tree_s *tree_prebuilt_objs = NULL;     /* XXX refactor */


static void setup_gcpage(void)
{
    char *base = stm_object_pages + END_NURSERY_PAGE * 4096UL;
    uintptr_t length = NB_SHARED_PAGES * 4096UL;
    _stm_largemalloc_init_arena(base, length);

    uninitialized_page_start = stm_object_pages + END_NURSERY_PAGE * 4096UL;
    uninitialized_page_stop  = uninitialized_page_start + NB_SHARED_PAGES * 4096UL;
}

static void teardown_gcpage(void)
{
    LIST_FREE(testing_prebuilt_objs);
    if (tree_prebuilt_objs != NULL) {
        tree_free(tree_prebuilt_objs);
        tree_prebuilt_objs = NULL;
    }
}



static void setup_N_pages(char *pages_addr, long num)
{
    /* make pages accessible in sharing segment only (pages already
       PROT_READ/WRITE (see setup.c), but not marked accessible as page
       status). */

    /* lock acquiring maybe not necessary because the affected pages don't
       need privatization protection. (but there is an assert right
       now to enforce that XXXXXX) */
    acquire_all_privatization_locks();

    uintptr_t p = (pages_addr - stm_object_pages) / 4096UL;
    dprintf(("setup_N_pages(%p, %lu): pagenum %lu\n", pages_addr, num, p));
    while (num-->0) {
        /* XXX: page_range_mark_accessible() */
        page_mark_accessible(0, p + num);
    }

    release_all_privatization_locks();
}


static uint8_t lock_growth_large = 0;

static stm_char *allocate_outside_nursery_large(uint64_t size)
{
    /* Allocate the object with largemalloc.c from the lower
       addresses.  Round up the size to a multiple of 16, rather than
       8, as a quick way to simplify the code in stm_write_card().
    */
    char *addr = _stm_large_malloc((size + 15) & ~15);
    if (addr == NULL)
        stm_fatalerror("not enough memory!");
    assert((((uintptr_t)addr) & 15) == 0);    /* alignment check */

    if (LIKELY(addr + size <= uninitialized_page_start)) {
        dprintf(("allocate_outside_nursery_large(%lu): %p, page=%lu\n",
                 size, (char*)(addr - stm_object_pages),
                 (uintptr_t)(addr - stm_object_pages) / 4096UL));

        /* set stm_flags to 0 in seg0 so that major gc will see them
           as not visited during sweeping */
        ((struct object_s*)addr)->stm_flags = 0;

        return (stm_char*)(addr - stm_object_pages);
    }


    /* uncommon case: need to initialize some more pages */
    stm_spinlock_acquire(lock_growth_large);

    char *start = uninitialized_page_start;
    if (addr + size > start) {
        uintptr_t npages;
        npages = (addr + size - start) / 4096UL;
        npages += GCPAGE_NUM_PAGES;
        if (uninitialized_page_stop - start < npages * 4096UL) {
            stm_fatalerror("out of memory!");   /* XXX */
        }
        setup_N_pages(start, npages);
        if (!__sync_bool_compare_and_swap(&uninitialized_page_start,
                                          start,
                                          start + npages * 4096UL)) {
            stm_fatalerror("uninitialized_page_start changed?");
        }
    }

    dprintf(("allocate_outside_nursery_large(%lu): %p, page=%lu\n",
             size, (char*)(addr - stm_object_pages),
             (uintptr_t)(addr - stm_object_pages) / 4096UL));

    ((struct object_s*)addr)->stm_flags = 0;

    stm_spinlock_release(lock_growth_large);
    return (stm_char*)(addr - stm_object_pages);
}

object_t *_stm_allocate_old(ssize_t size_rounded_up)
{
    /* only for tests xxx but stm_setup_prebuilt() uses this now too */
    if (size_rounded_up <= GC_LAST_SMALL_SIZE)
        return _stm_allocate_old_small(size_rounded_up);

    stm_char *p = allocate_outside_nursery_large(size_rounded_up);
    object_t *o = (object_t *)p;

    /* Sharing seg0 needs to be current, because in core.c handle_segfault_in_page,
       we depend on simply copying the page from seg0 if it was never accessed by
       anyone so far (we only run in seg1 <= seg < NB_SEGMENT). */
    assert(STM_SEGMENT->segment_num == 0);
    memset(REAL_ADDRESS(STM_SEGMENT->segment_base, o), 0, size_rounded_up);
    o->stm_flags = GCFLAG_WRITE_BARRIER;

    if (testing_prebuilt_objs == NULL)
        testing_prebuilt_objs = list_create();
    LIST_APPEND(testing_prebuilt_objs, o);

    dprintf(("allocate_old(%lu): %p, seg=%d, page=%lu\n",
             size_rounded_up, p,
             get_segment_of_linear_address(stm_object_pages + (uintptr_t)p),
             (uintptr_t)p / 4096UL));
    return o;
}

static void _fill_preexisting_slice(long segnum, char *dest,
                                    const char *src, uintptr_t size)
{
    uintptr_t np = dest - get_segment_base(segnum);
    if (get_page_status_in(segnum, np / 4096) != PAGE_NO_ACCESS)
        memcpy(dest, src, size);
}

object_t *stm_allocate_preexisting(ssize_t size_rounded_up,
                                   const char *initial_data)
{
    stm_char *np = allocate_outside_nursery_large(size_rounded_up);
    uintptr_t nobj = (uintptr_t)np;
    dprintf(("allocate_preexisting: %p\n", (object_t *)nobj));

    char *nobj_seg0 = stm_object_pages + nobj;
    memcpy(nobj_seg0, initial_data, size_rounded_up);
    ((struct object_s *)nobj_seg0)->stm_flags = GCFLAG_WRITE_BARRIER;

    acquire_privatization_lock(STM_SEGMENT->segment_num);
    DEBUG_EXPECT_SEGFAULT(false);

    long j;
    for (j = 1; j < NB_SEGMENTS; j++) {
        const char *src = nobj_seg0;
        char *dest = get_segment_base(j) + nobj;
        char *end = dest + size_rounded_up;

        while (((uintptr_t)dest) / 4096 != ((uintptr_t)end - 1) / 4096) {
            uintptr_t count = 4096 - (((uintptr_t)dest) & 4095);
            _fill_preexisting_slice(j, dest, src, count);
            src += count;
            dest += count;
        }
        _fill_preexisting_slice(j, dest, src, end - dest);

#ifdef STM_TESTS
        /* can't really enable this check outside tests, because there is
           a change that the transaction_state changes in parallel */
        if (get_priv_segment(j)->transaction_state != TS_NONE) {
            assert(!was_read_remote(get_segment_base(j), (object_t *)nobj));
        }
#endif
    }

    DEBUG_EXPECT_SEGFAULT(true);
    release_privatization_lock(STM_SEGMENT->segment_num);

    stm_write_fence();     /* make sure 'nobj' is fully initialized from
                          all threads here */
    return (object_t *)nobj;
}

/************************************************************/


static void major_collection_with_mutex(void)
{
    timing_event(STM_SEGMENT->running_thread, STM_GC_MAJOR_START);

    synchronize_all_threads(STOP_OTHERS_UNTIL_MUTEX_UNLOCK);

    if (is_major_collection_requested()) {   /* if *still* true */
        major_collection_now_at_safe_point();
    }

    timing_event(STM_SEGMENT->running_thread, STM_GC_MAJOR_DONE);
}

static void major_collection_if_requested(void)
{
    assert(!_has_mutex());
    if (!is_major_collection_requested())
        return;

    s_mutex_lock();

    if (is_major_collection_requested()) {   /* if still true */
        major_collection_with_mutex();
    }

    s_mutex_unlock();
    exec_local_finalizers();
}


/************************************************************/

/* objects to trace are traced in the sharing seg0 or in a
   certain segment if there exist modifications there.
   All other segments' versions should be identical to seg0's
   version and thus don't need tracing. */
static struct list_s *marked_objects_to_trace;

/* a list of hobj/hashtable pairs for all hashtables seen */
static struct list_s *all_hashtables_seen = NULL;

/* we use the sharing seg0's pages for the GCFLAG_VISITED flag */

static inline struct object_s *mark_loc(object_t *obj)
{
    /* uses the memory in seg0 for marking: */
    struct object_s *result = (struct object_s*)REAL_ADDRESS(stm_object_pages, obj);
    return result;
}

static inline bool mark_visited_test(object_t *obj)
{
    struct object_s *realobj = mark_loc(obj);
    return !!(realobj->stm_flags & GCFLAG_VISITED);
}

static inline bool mark_visited_test_and_set(object_t *obj)
{
    struct object_s *realobj = mark_loc(obj);
    if (realobj->stm_flags & GCFLAG_VISITED) {
        return true;
    }
    else {
        realobj->stm_flags |= GCFLAG_VISITED;
        return false;
    }
}

static inline bool mark_visited_test_and_clear(object_t *obj)
{
    struct object_s *realobj = mark_loc(obj);
    if (realobj->stm_flags & GCFLAG_VISITED) {
        realobj->stm_flags &= ~GCFLAG_VISITED;
        return true;
    }
    else {
        return false;
    }
}


/************************************************************/

static bool is_overflow_obj_safe(struct stm_priv_segment_info_s *pseg, object_t *obj)
{
    /* this function first also checks if the page is accessible in order
       to not cause segfaults during major gc (it does exactly the same
       as IS_OVERFLOW_OBJ otherwise) */
    if (get_page_status_in(pseg->pub.segment_num, (uintptr_t)obj / 4096UL) == PAGE_NO_ACCESS)
        return false;

    struct object_s *realobj = (struct object_s*)REAL_ADDRESS(pseg->pub.segment_base, obj);
    return IS_OVERFLOW_OBJ(pseg, realobj);
}


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

    LIST_APPEND(marked_objects_to_trace, obj);
}


static void mark_and_trace(
    object_t *obj,
    char *segment_base, /* to trace obj in */
    struct stm_priv_segment_info_s *pseg) /* to trace children in */
{
    /* mark the obj and trace all reachable objs from it */

    assert(list_is_empty(marked_objects_to_trace));

    /* trace into the object (the version from 'segment_base') */
    struct object_s *realobj =
        (struct object_s *)REAL_ADDRESS(segment_base, obj);
    stmcb_trace(realobj, &mark_record_trace);

    /* trace all references found in sharing seg0 (should always be
       up-to-date and not cause segfaults, except for overflow objs) */
    segment_base = pseg->pub.segment_base;
    while (!list_is_empty(marked_objects_to_trace)) {
        obj = (object_t *)list_pop_item(marked_objects_to_trace);

        char *base = is_overflow_obj_safe(pseg, obj) ? segment_base : stm_object_pages;
        realobj = (struct object_s *)REAL_ADDRESS(base, obj);
        stmcb_trace(realobj, &mark_record_trace);
    }
}

static inline void mark_visit_object(
    object_t *obj,
    char *segment_base, /* to trace ojb in */
    struct stm_priv_segment_info_s *pseg) /* to trace children in */
{
    /* if already visited, don't trace */
    if (obj == NULL || mark_visited_test_and_set(obj))
        return;
    mark_and_trace(obj, segment_base, pseg);
}


static void mark_visit_possibly_overflow_object(object_t *obj, struct stm_priv_segment_info_s *pseg)
{
    /* if newly allocated object, we trace in segment_base, otherwise in
       the sharing seg0 */
    if (obj == NULL)
        return;

    if (is_overflow_obj_safe(pseg, obj)) {
        mark_visit_object(obj, pseg->pub.segment_base, pseg);
    } else {
        mark_visit_object(obj, stm_object_pages, pseg);
    }
}

static void *mark_visit_objects_from_ss(void *_, const void *slice, size_t size)
{
    const struct stm_shadowentry_s *p, *end;
    p = (const struct stm_shadowentry_s *)slice;
    end = (const struct stm_shadowentry_s *)(slice + size);
    for (; p < end; p++)
        if ((((uintptr_t)p->ss) & 3) == 0) {
            mark_visit_object(p->ss, stm_object_pages, // seg0
                              /* there should be no overflow objs not already
                                 visited, so any pseg is fine really: */
                              get_priv_segment(STM_SEGMENT->segment_num));
        }
    return NULL;
}

static void assert_obj_accessible_in(long segnum, object_t *obj)
{
#ifndef NDEBUG
    uintptr_t page = (uintptr_t)obj / 4096UL;
    assert(get_page_status_in(segnum, page) == PAGE_ACCESSIBLE);

    struct object_s *realobj =
        (struct object_s *)REAL_ADDRESS(get_segment_base(segnum), obj);

    size_t obj_size = stmcb_size_rounded_up(realobj);
    uintptr_t count = obj_size / 4096UL + 1;
    while (count--> 0) {
        assert(get_page_status_in(segnum, page) == PAGE_ACCESSIBLE);
        page++;
    }
#endif
}



static void mark_visit_from_modified_objects(void)
{
    /* look for modified objects in segments and mark all of them
       for further tracing (XXX: don't if we are going to share
       some of the pages) */

    long i;
    struct list_s *uniques = list_create();

    for (i = 1; i < NB_SEGMENTS; i++) {
        char *base = get_segment_base(i);
        OPT_ASSERT(list_is_empty(uniques));

        /* the mod_old_objects list may contain maanny slices for
           the same *huge* object. it seems worth to first construct
           a list of unique objects. we use the VISITED flag for this
           purpose as it is never set outside of seg0: */
        struct list_s *lst = get_priv_segment(i)->modified_old_objects;

        struct stm_undo_s *modified = (struct stm_undo_s *)lst->items;
        struct stm_undo_s *end = (struct stm_undo_s *)(lst->items + lst->count);
        for (; modified < end; modified++) {
            if (modified->type == TYPE_POSITION_MARKER)
                continue;
            object_t *obj = modified->object;
            struct object_s *dst = (struct object_s*)REAL_ADDRESS(base, obj);

            if (!(dst->stm_flags & GCFLAG_VISITED)) {
                LIST_APPEND(uniques, obj);
                dst->stm_flags |= GCFLAG_VISITED;
            }
        }

        LIST_FOREACH_R(uniques, object_t*,
           ({
               /* clear the VISITED flags again and actually visit them */
               struct object_s *dst = (struct object_s*)REAL_ADDRESS(base, item);
               dst->stm_flags &= ~GCFLAG_VISITED;

               /* All modified objs have all pages accessible for now.
                  This is because we create a backup of the whole obj
                  and thus make all pages accessible. */
               assert_obj_accessible_in(i, item);

               assert(!is_overflow_obj_safe(get_priv_segment(i), item)); /* should never be in that list */

               if (!mark_visited_test_and_set(item)) {
                   /* trace shared, committed version: only do this if we didn't
                      trace it already. This is safe because we don't trace any
                      objs before mark_visit_from_modified_objects AND if we
                      do mark_and_trace on an obj that is modified in >1 segment,
                      the tracing always happens in seg0 (see mark_and_trace). */
                   mark_and_trace(item, stm_object_pages, get_priv_segment(i));
               }
               mark_and_trace(item, base, get_priv_segment(i));   /* private, modified version */
           }));

        list_clear(uniques);
    }
    LIST_FREE(uniques);
}

static void mark_visit_from_markers(void)
{
    long i;
    for (i = 1; i < NB_SEGMENTS; i++) {
        struct stm_priv_segment_info_s *pseg = get_priv_segment(i);
        struct list_s *lst = get_priv_segment(i)->modified_old_objects;

        struct stm_undo_s *modified = (struct stm_undo_s *)lst->items;
        struct stm_undo_s *end = (struct stm_undo_s *)(lst->items + lst->count);
        for (; modified < end; modified++) {
            if (modified->type == TYPE_POSITION_MARKER &&
                    modified->type2 != TYPE_MODIFIED_HASHTABLE)
                mark_visit_possibly_overflow_object(modified->marker_object, pseg);
        }
    }
}

static void mark_visit_from_roots(void)
{
    if (testing_prebuilt_objs != NULL) {
        LIST_FOREACH_R(testing_prebuilt_objs, object_t * /*item*/,
                   mark_visit_object(item, stm_object_pages, // seg0
                                     /* any pseg is fine, as we already traced modified
                                        objs and thus covered all overflow objs reachable
                                        from here */
                                     get_priv_segment(STM_SEGMENT->segment_num)));
    }

    stm_thread_local_t *tl = stm_all_thread_locals;
    do {
        /* look at all objs on the shadow stack (they are old but may
           be uncommitted so far, so only exist in the associated_segment_num).

           IF they are uncommitted overflow objs, trace in the actual segment,
           otherwise, since we just executed a minor collection, they were
           all synced to the sharing seg0. Thus we can trace them there.

           If they were again modified since then, they were traced
           by mark_visit_from_modified_object() already.
        */

        /* only for new, uncommitted objects:
           If 'tl' is currently running, its 'last_associated_segment_num'
           field is the segment number that contains the correct
           version of its overflowed objects. */
        struct stm_priv_segment_info_s *pseg = get_priv_segment(tl->last_associated_segment_num);

        struct stm_shadowentry_s *current = tl->shadowstack;
        struct stm_shadowentry_s *base = tl->shadowstack_base;
        while (current-- != base) {
            if ((((uintptr_t)current->ss) & 3) == 0) {
                mark_visit_possibly_overflow_object(current->ss, pseg);
            }
        }

        mark_visit_possibly_overflow_object(tl->thread_local_obj, pseg);

        tl = tl->next;
    } while (tl != stm_all_thread_locals);

    /* also visit all objs in the rewind-shadowstack */
    long i;
    assert(get_priv_segment(0)->transaction_state == TS_NONE);
    for (i = 1; i < NB_SEGMENTS; i++) {
        if (get_priv_segment(i)->transaction_state != TS_NONE) {
            mark_visit_possibly_overflow_object(
                get_priv_segment(i)->threadlocal_at_start_of_transaction,
                get_priv_segment(i));

            stm_rewind_jmp_enum_shadowstack(
                get_segment(i)->running_thread,
                mark_visit_objects_from_ss);
        }
    }
}


static void clean_up_segment_lists(void)
{
#pragma push_macro("STM_PSEGMENT")
#pragma push_macro("STM_SEGMENT")
#undef STM_PSEGMENT
#undef STM_SEGMENT

    long i;
    for (i = 1; i < NB_SEGMENTS; i++) {
        struct stm_priv_segment_info_s *pseg = get_priv_segment(i);
        struct list_s *lst;

        /* 'objects_pointing_to_nursery' should be empty, but isn't
           necessarily because it also lists objects that have been
           written to but don't actually point to the nursery.  Clear
           it up and set GCFLAG_WRITE_BARRIER again on the objects.
           This is the case for transactions where
               MINOR_NOTHING_TO_DO() == true
           but they still did write-barriers on objects
           (the objs are still in modified_old_objects list)
        */
        lst = pseg->objects_pointing_to_nursery;
        if (!list_is_empty(lst)) {
            LIST_FOREACH_R(lst, object_t* /*item*/,
                ({
                    struct object_s *realobj = (struct object_s *)
                        REAL_ADDRESS(pseg->pub.segment_base, (uintptr_t)item);
                    assert(!(realobj->stm_flags & GCFLAG_WRITE_BARRIER));
                    realobj->stm_flags |= GCFLAG_WRITE_BARRIER;

                    OPT_ASSERT(!(realobj->stm_flags & GCFLAG_CARDS_SET));
                }));
            list_clear(lst);
        } else {
            /* if here MINOR_NOTHING_TO_DO() was true before, it's like
               we "didn't do a collection" at all. So nothing to do on
               modified_old_objs. */
        }

        lst = pseg->old_objects_with_cards_set;
        LIST_FOREACH_R(lst, object_t* /*item*/,
            ({
                struct object_s *realobj = (struct object_s *)
                    REAL_ADDRESS(pseg->pub.segment_base, item);
                OPT_ASSERT(realobj->stm_flags & GCFLAG_WRITE_BARRIER);

                /* mark marked cards as old if it survives, otherwise
                   CLEAR, as their spot could get reused */
                uint8_t mark_value = mark_visited_test(item) ?
                    pseg->pub.transaction_read_version : CARD_CLEAR;
                _reset_object_cards(pseg, item, mark_value, false,
                                    mark_value == CARD_CLEAR);
            }));
        list_clear(lst);


        /* remove from large_overflow_objects all objects that die */
        lst = pseg->large_overflow_objects;
        uintptr_t n = list_count(lst);
        while (n-- > 0) {
            object_t *obj = (object_t *)list_item(lst, n);
            if (!mark_visited_test(obj)) {
                if (obj_should_use_cards(pseg->pub.segment_base, obj))
                    _reset_object_cards(pseg, obj, CARD_CLEAR, false, true);
                list_set_item(lst, n, list_pop_item(lst));
            }
        }

        /* Remove from 'modified_old_objects' all old hashtables that die */
        {
            lst = pseg->modified_old_objects;
            uintptr_t j, k = 0, limit = list_count(lst);
            for (j = 0; j < limit; j += 3) {
                uintptr_t e0 = list_item(lst, j + 0);
                uintptr_t e1 = list_item(lst, j + 1);
                uintptr_t e2 = list_item(lst, j + 2);
                if (e0 == TYPE_POSITION_MARKER &&
                    e1 == TYPE_MODIFIED_HASHTABLE &&
                    !mark_visited_test((object_t *)e2)) {
                    /* hashtable object dies */
                }
                else {
                    if (j != k) {
                        list_set_item(lst, k + 0, e0);
                        list_set_item(lst, k + 1, e1);
                        list_set_item(lst, k + 2, e2);
                    }
                    k += 3;
                }
            }
            lst->count = k;
        }
    }
#pragma pop_macro("STM_SEGMENT")
#pragma pop_macro("STM_PSEGMENT")
}


static inline bool largemalloc_keep_object_at(char *data)
{
    /* XXX: identical to smallmalloc_keep_object_at()? */
    /* this is called by _stm_largemalloc_sweep() */
    object_t *obj = (object_t *)(data - stm_object_pages);
    //dprintf(("keep obj %p ? -> %d\n", obj, mark_visited_test(obj)));
    if (!mark_visited_test_and_clear(obj)) {
        /* This is actually needed in order to avoid random write-read
           conflicts with objects read and freed long in the past.
           It is probably rare enough, but still, we want to avoid any
           false conflict. (test_random hits it sometimes) */
        long i;
        for (i = 1; i < NB_SEGMENTS; i++) {
            /* reset read marker */
            ((struct stm_read_marker_s *)
             (get_segment_base(i) + (((uintptr_t)obj) >> 4)))->rm = 0;
        }
        return false;
    }
    return true;
}

static void sweep_large_objects(void)
{
    _stm_largemalloc_sweep();
}

static inline bool smallmalloc_keep_object_at(char *data)
{
    /* XXX: identical to largemalloc_keep_object_at()? */
    /* this is called by _stm_smallmalloc_sweep() */
    object_t *obj = (object_t *)(data - stm_object_pages);
    //dprintf(("keep small obj %p ? -> %d\n", obj, mark_visited_test(obj)));
    if (!mark_visited_test_and_clear(obj)) {
        /* This is actually needed in order to avoid random write-read
           conflicts with objects read and freed long in the past.
           It is probably rare enough, but still, we want to avoid any
           false conflict. (test_random hits it sometimes) */
        long i;
        for (i = 1; i < NB_SEGMENTS; i++) {
            /* reset read marker */
            ((struct stm_read_marker_s *)
             (get_segment_base(i) + (((uintptr_t)obj) >> 4)))->rm = 0;
        }
        return false;
    }
    return true;
}

static void sweep_small_objects(void)
{
    _stm_smallmalloc_sweep();
}

static void clean_up_commit_log_entries(void)
{
    struct stm_commit_log_entry_s *cl, *next;

#ifndef NDEBUG
    /* check that all segments are at the same revision: */
    cl = get_priv_segment(0)->last_commit_log_entry;
    for (long i = 0; i < NB_SEGMENTS; i++) {
        struct stm_priv_segment_info_s *pseg = get_priv_segment(i);
        assert(pseg->last_commit_log_entry == cl);
    }
#endif

    /* if there is only one element, we don't have to do anything: */
    cl = &commit_log_root;

    if (cl->next == NULL || cl->next == INEV_RUNNING) {
        assert(get_priv_segment(0)->last_commit_log_entry == cl);
        return;
    }

    bool was_inev = false;
    uint64_t rev_num = -1;

    next = cl->next;   /* guaranteed to exist */
    do {
        cl = next;
        rev_num = cl->rev_num;

        /* free bk copies of entries: */
        long count = cl->written_count;
        while (count-->0) {
            if (cl->written[count].type != TYPE_POSITION_MARKER)
                free_bk(&cl->written[count]);
        }

        next = cl->next;
        free_cle(cl);
        if (next == INEV_RUNNING) {
            was_inev = true;
            break;
        }
    } while (next != NULL);

    /* set the commit_log_root to the last, common cl entry: */
    commit_log_root.next = was_inev ? INEV_RUNNING : NULL;
    commit_log_root.rev_num = rev_num;

    /* update in all segments: */
    for (long i = 0; i < NB_SEGMENTS; i++) {
        get_priv_segment(i)->last_commit_log_entry = &commit_log_root;
    }

    assert(_stm_count_cl_entries() == 0);
}



static void major_collection_now_at_safe_point(void)
{
    dprintf(("\n"));
    dprintf((" .----- major collection -----------------------\n"));
    assert(_has_mutex());

    /* first, force a minor collection in each of the other segments */
    major_do_validation_and_minor_collections();

    dprintf((" | used before collection: %ld\n",
             (long)pages_ctl.total_allocated));
    dprintf((" | commit log entries before: %ld\n",
             _stm_count_cl_entries()));


    /* free all commit log entries. all segments are on the most recent
       revision now. */
    uint64_t allocd_before = pages_ctl.total_allocated;
    clean_up_commit_log_entries();
    /* check if freeing the log entries actually freed a considerable
       amount itself. Then we don't want to also trace the whole heap
       and just leave major gc right here.
       The problem is apparent from raytrace.py, but may disappear if
       we have card marking that also reduces the size of commit log
       entries */
    if ((pages_ctl.total_allocated < pages_ctl.total_allocated_bound)
        && (allocd_before - pages_ctl.total_allocated > 0.3 * allocd_before)) {
        /* 0.3 should mean that we are at about 50% of the way to the
           allocated_bound again */
#ifndef STM_TESTS
        /* we freed a considerable amount just by freeing commit log entries */
        pages_ctl.major_collection_requested = false; // reset_m_gc_requested

        dprintf(("STOP AFTER FREEING CL ENTRIES: -%ld\n",
                 (long)(allocd_before - pages_ctl.total_allocated)));
        dprintf((" | used after collection:  %ld\n",
                (long)pages_ctl.total_allocated));
        dprintf((" `----------------------------------------------\n"));
        if (must_abort())
            abort_with_mutex();

        return;
#endif
    }

    /* only necessary because of assert that fails otherwise (XXX) */
    acquire_all_privatization_locks();

    DEBUG_EXPECT_SEGFAULT(false);

    /* marking */
    LIST_CREATE(marked_objects_to_trace);
    LIST_CREATE(all_hashtables_seen);
    mark_visit_from_modified_objects();
    mark_visit_from_markers();
    mark_visit_from_roots();
    mark_visit_from_active_queues();
    mark_visit_from_finalizer_pending();

    /* finalizer support: will mark as visited all objects with a
       finalizer and all objects reachable from there, and also moves
       some objects from 'objects_with_finalizers' to 'run_finalizers'. */
    deal_with_objects_with_finalizers();

    LIST_FREE(marked_objects_to_trace);

    /* weakrefs and execute old destructors */
    stm_visit_old_weakrefs();
    deal_with_old_objects_with_destructors();

    /* cleanup */
    clean_up_segment_lists();

    /* sweeping */
    sweep_large_objects();
    sweep_small_objects();

    /* hashtables */
    stm_compact_hashtables();
    LIST_FREE(all_hashtables_seen);

    dprintf((" | used after collection:  %ld\n",
             (long)pages_ctl.total_allocated));
    dprintf((" `----------------------------------------------\n"));

    reset_major_collection_requested();

    DEBUG_EXPECT_SEGFAULT(true);

    release_all_privatization_locks();

    /* if major_do_validation_and_minor_collections() decided that we
       must abort, do it now. The others are in safe-points that will
       abort if they need to. */
    dprintf(("must abort?:%d\n", (int)must_abort()));
    if (must_abort())
        abort_with_mutex();
}
