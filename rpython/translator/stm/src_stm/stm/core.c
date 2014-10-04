/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


static void teardown_core(void)
{
    memset(write_locks, 0, sizeof(write_locks));
}

#ifdef NDEBUG
#define EVENTUALLY(condition)    /* nothing */
#else
#define EVENTUALLY(condition)                                   \
    {                                                           \
        if (!(condition)) {                                     \
            acquire_privatization_lock();                       \
            if (!(condition))                                   \
                stm_fatalerror("fails: " #condition);           \
            release_privatization_lock();                       \
        }                                                       \
    }
#endif

static void check_flag_write_barrier(object_t *obj)
{
    /* check that all copies of the object, apart from mine, have the
       GCFLAG_WRITE_BARRIER.  (a bit messy because it's possible that we
       read a page in the middle of privatization by another thread)
    */
#ifndef NDEBUG
    long i;
    struct object_s *o1;
    for (i = 0; i <= NB_SEGMENTS; i++) {
        if (i == STM_SEGMENT->segment_num)
            continue;
        o1 = (struct object_s *)REAL_ADDRESS(get_segment_base(i), obj);
        EVENTUALLY(o1->stm_flags & GCFLAG_WRITE_BARRIER);
    }
#endif
}

__attribute__((always_inline))
static void write_slowpath_overflow_obj(object_t *obj, bool mark_card)
{
    /* An overflow object is an object from the same transaction, but
       outside the nursery.  More precisely, it is no longer young,
       i.e. it comes from before the most recent minor collection.
    */
    assert(STM_PSEGMENT->objects_pointing_to_nursery != NULL);

    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);
    if (!mark_card) {
        /* The basic case, with no card marking.  We append the object
           into 'objects_pointing_to_nursery', and remove the flag so
           that the write_slowpath will not be called again until the
           next minor collection. */
        if (obj->stm_flags & GCFLAG_CARDS_SET) {
            /* if we clear this flag, we also need to clear the cards */
            _reset_object_cards(get_priv_segment(STM_SEGMENT->segment_num),
                                obj, CARD_CLEAR, false);
        }
        obj->stm_flags &= ~(GCFLAG_WRITE_BARRIER | GCFLAG_CARDS_SET);
        LIST_APPEND(STM_PSEGMENT->objects_pointing_to_nursery, obj);
    }
    else {
        /* Card marking.  Don't remove GCFLAG_WRITE_BARRIER because we
           need to come back to _stm_write_slowpath_card() for every
           card to mark.  Add GCFLAG_CARDS_SET. */
        assert(!(obj->stm_flags & GCFLAG_CARDS_SET));
        obj->stm_flags |= GCFLAG_CARDS_SET;
        assert(STM_PSEGMENT->old_objects_with_cards);
        LIST_APPEND(STM_PSEGMENT->old_objects_with_cards, obj);
    }
}

__attribute__((always_inline))
static void write_slowpath_common(object_t *obj, bool mark_card)
{
    assert(_seems_to_be_running_transaction());
    assert(!_is_young(obj));
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);

    uintptr_t base_lock_idx = get_write_lock_idx((uintptr_t)obj);

    if (IS_OVERFLOW_OBJ(STM_PSEGMENT, obj)) {
        assert(write_locks[base_lock_idx] == 0);
        write_slowpath_overflow_obj(obj, mark_card);
        return;
    }
    /* Else, it's an old object and we need to privatise it.
       Do a read-barrier now.  Note that this must occur before the
       safepoints that may be issued in write_write_contention_management().
    */
    stm_read(obj);

    /* Take the segment's own lock number */
    uint8_t lock_num = STM_PSEGMENT->write_lock_num;

    /* If CARDS_SET, we entered here at least once already, so we
       already own the write_lock */
    assert(IMPLY(obj->stm_flags & GCFLAG_CARDS_SET,
                 write_locks[base_lock_idx] == lock_num));

    /* XXX XXX XXX make the logic of write-locking objects optional! */

    /* claim the write-lock for this object.  In case we're running the
       same transaction since a long while, the object can be already in
       'modified_old_objects' (but, because it had GCFLAG_WRITE_BARRIER,
       not in 'objects_pointing_to_nursery').  We'll detect this case
       by finding that we already own the write-lock. */

 retry:
    if (write_locks[base_lock_idx] == 0) {
        /* A lock to prevent reading garbage from
           lookup_other_thread_recorded_marker() */
        acquire_marker_lock(STM_SEGMENT->segment_base);

        if (UNLIKELY(!__sync_bool_compare_and_swap(&write_locks[base_lock_idx],
                                                   0, lock_num))) {
            release_marker_lock(STM_SEGMENT->segment_base);
            goto retry;
        }

        dprintf_test(("write_slowpath %p -> mod_old\n", obj));

        /* Add the current marker, recording where we wrote to this object */
        timing_record_write();

        /* Change to this old object from this transaction.
           Add it to the list 'modified_old_objects'. */
        LIST_APPEND(STM_PSEGMENT->modified_old_objects, obj);

        release_marker_lock(STM_SEGMENT->segment_base);

        /* We need to privatize the pages containing the object, if they
           are still SHARED_PAGE.  The common case is that there is only
           one page in total. */
        uintptr_t first_page = ((uintptr_t)obj) / 4096UL;

        /* If the object is in the uniform pages of small objects
           (outside the nursery), then it fits into one page.  This is
           the common case. Otherwise, we need to compute it based on
           its location and size. */
        if ((obj->stm_flags & GCFLAG_SMALL_UNIFORM) != 0) {
            page_privatize(first_page);
        }
        else {
            char *realobj;
            size_t obj_size;
            uintptr_t i, end_page;

            /* get the size of the object */
            realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
            obj_size = stmcb_size_rounded_up((struct object_s *)realobj);

            /* get the last page containing data from the object */
            end_page = (((uintptr_t)obj) + obj_size - 1) / 4096UL;

            for (i = first_page; i <= end_page; i++) {
                page_privatize(i);
            }
        }
    }
    else if (write_locks[base_lock_idx] == lock_num) {
#ifdef STM_TESTS
        bool found = false;
        LIST_FOREACH_R(STM_PSEGMENT->modified_old_objects, object_t *,
                       ({ if (item == obj) { found = true; break; } }));
        assert(found);
#endif
    }
    else {
        /* call the contention manager, and then retry (unless we were
           aborted). */
        write_write_contention_management(base_lock_idx, obj);
        goto retry;
    }


    /* check that we really have a private page */
    assert(is_private_page(STM_SEGMENT->segment_num,
                           ((uintptr_t)obj) / 4096));

    /* check that so far all copies of the object have the flag */
    check_flag_write_barrier(obj);

    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);
    if (!mark_card) {
        /* A common case for write_locks[] that was either 0 or lock_num:
           we need to add the object to the appropriate list if there is one.
        */
        if (STM_PSEGMENT->objects_pointing_to_nursery != NULL) {
            dprintf_test(("write_slowpath %p -> old obj_to_nurs\n", obj));
            LIST_APPEND(STM_PSEGMENT->objects_pointing_to_nursery, obj);
        }

        if (obj->stm_flags & GCFLAG_CARDS_SET) {
            /* if we clear this flag, we have to tell sync_old_objs that
               everything needs to be synced */
            _reset_object_cards(get_priv_segment(STM_SEGMENT->segment_num),
                                obj, CARD_MARKED_OLD, true); /* mark all */
        }

        /* remove GCFLAG_WRITE_BARRIER if we succeeded in getting the base
           write-lock (not for card marking). */
        obj->stm_flags &= ~(GCFLAG_WRITE_BARRIER | GCFLAG_CARDS_SET);
    }
    else {
        /* don't remove WRITE_BARRIER, but add CARDS_SET */
        obj->stm_flags |= GCFLAG_CARDS_SET;
        assert(STM_PSEGMENT->old_objects_with_cards);
        LIST_APPEND(STM_PSEGMENT->old_objects_with_cards, obj);
    }

    /* for sanity, check again that all other segment copies of this
       object still have the flag (so privatization worked) */
    check_flag_write_barrier(obj);
}

void _stm_write_slowpath(object_t *obj)
{
    write_slowpath_common(obj, /*mark_card=*/false);
}

static bool obj_should_use_cards(object_t *obj)
{
    struct object_s *realobj = (struct object_s *)
        REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    long supports = stmcb_obj_supports_cards(realobj);
    if (!supports)
        return 0;

    /* check also if it makes sense: */
    size_t size = stmcb_size_rounded_up(realobj);
    return (size >= _STM_MIN_CARD_OBJ_SIZE);
}

char _stm_write_slowpath_card_extra(object_t *obj)
{
    /* the PyPy JIT calls this function directly if it finds that an
       array doesn't have the GCFLAG_CARDS_SET */
    bool mark_card = obj_should_use_cards(obj);
    write_slowpath_common(obj, mark_card);
    return mark_card;
}

long _stm_write_slowpath_card_extra_base(void)
{
    /* for the PyPy JIT: _stm_write_slowpath_card_extra_base[obj >> 4]
       is the byte that must be set to CARD_MARKED.  The logic below
       does the same, but more explicitly. */
    return (((long)write_locks) - WRITELOCK_START + 1)
        + 0x4000000000000000L;   // <- workaround for a clang bug :-(
}

void _stm_write_slowpath_card(object_t *obj, uintptr_t index)
{
    /* If CARDS_SET is not set so far, issue a normal write barrier.
       If the object is large enough, ask it to set up the object for
       card marking instead.
    */
    if (!(obj->stm_flags & GCFLAG_CARDS_SET)) {
        char mark_card = _stm_write_slowpath_card_extra(obj);
        if (!mark_card)
            return;
    }

    dprintf_test(("write_slowpath_card %p -> index:%lu\n",
                  obj, index));

    /* We reach this point if we have to mark the card.
     */
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);
    assert(obj->stm_flags & GCFLAG_CARDS_SET);
    assert(!(obj->stm_flags & GCFLAG_SMALL_UNIFORM)); /* not supported/tested */

#ifndef NDEBUG
    struct object_s *realobj = (struct object_s *)
        REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    size_t size = stmcb_size_rounded_up(realobj);
    /* we need at least one lock in addition to the STM-reserved object
       write-lock */
    assert(size >= 32);
    /* the 'index' must be in range(length-of-obj), but we don't have
       a direct way to know the length.  We know that it is smaller
       than the size in bytes. */
    assert(index < size);
#endif

    /* Write into the card's lock.  This is used by the next minor
       collection to know what parts of the big object may have changed.
       We already own the object here or it is an overflow obj. */
    uintptr_t base_lock_idx = get_write_lock_idx((uintptr_t)obj);
    uintptr_t card_lock_idx = base_lock_idx + get_index_to_card_index(index);
    write_locks[card_lock_idx] = CARD_MARKED;

    /* More debug checks */
    dprintf(("mark %p index %lu, card:%lu with %d\n",
             obj, index, get_index_to_card_index(index), CARD_MARKED));
    assert(IMPLY(IS_OVERFLOW_OBJ(STM_PSEGMENT, obj),
                 write_locks[base_lock_idx] == 0));
    assert(IMPLY(!IS_OVERFLOW_OBJ(STM_PSEGMENT, obj),
                 write_locks[base_lock_idx] == STM_PSEGMENT->write_lock_num));
}

static void reset_transaction_read_version(void)
{
    /* force-reset all read markers to 0 */

    char *readmarkers = REAL_ADDRESS(STM_SEGMENT->segment_base,
                                     FIRST_READMARKER_PAGE * 4096UL);
    dprintf(("reset_transaction_read_version: %p %ld\n", readmarkers,
             (long)(NB_READMARKER_PAGES * 4096UL)));
    if (mmap(readmarkers, NB_READMARKER_PAGES * 4096UL,
             PROT_READ | PROT_WRITE,
             MAP_FIXED | MAP_PAGES_FLAGS, -1, 0) != readmarkers) {
        /* fall-back */
#if STM_TESTS
        stm_fatalerror("reset_transaction_read_version: %m");
#endif
        memset(readmarkers, 0, NB_READMARKER_PAGES * 4096UL);
    }
    STM_SEGMENT->transaction_read_version = 1;
}

static uint64_t _global_start_time = 0;

static void _stm_start_transaction(stm_thread_local_t *tl)
{
    assert(!_stm_in_transaction(tl));

    while (!acquire_thread_segment(tl))
        ;
    /* GS invalid before this point! */

    assert(STM_PSEGMENT->safe_point == SP_NO_TRANSACTION);
    assert(STM_PSEGMENT->transaction_state == TS_NONE);
    timing_event(tl, STM_TRANSACTION_START);
    STM_PSEGMENT->start_time = _global_start_time++;
    STM_PSEGMENT->signalled_to_commit_soon = false;
    STM_PSEGMENT->safe_point = SP_RUNNING;
    STM_PSEGMENT->marker_inev.object = NULL;
    STM_PSEGMENT->transaction_state = TS_REGULAR;
#ifndef NDEBUG
    STM_PSEGMENT->running_pthread = pthread_self();
#endif
    STM_PSEGMENT->shadowstack_at_start_of_transaction = tl->shadowstack;
    STM_PSEGMENT->threadlocal_at_start_of_transaction = tl->thread_local_obj;

    enter_safe_point_if_requested();
    dprintf(("start_transaction\n"));

    s_mutex_unlock();

    /* Now running the SP_RUNNING start.  We can set our
       'transaction_read_version' after releasing the mutex,
       because it is only read by a concurrent thread in
       stm_commit_transaction(), which waits until SP_RUNNING
       threads are paused.
    */
    uint8_t old_rv = STM_SEGMENT->transaction_read_version;
    STM_SEGMENT->transaction_read_version = old_rv + 1;
    if (UNLIKELY(old_rv == 0xff)) {
        reset_transaction_read_version();
    }

    assert(list_is_empty(STM_PSEGMENT->modified_old_objects));
    assert(list_is_empty(STM_PSEGMENT->modified_old_objects_markers));
    assert(list_is_empty(STM_PSEGMENT->young_weakrefs));
    assert(tree_is_cleared(STM_PSEGMENT->young_outside_nursery));
    assert(tree_is_cleared(STM_PSEGMENT->nursery_objects_shadows));
    assert(tree_is_cleared(STM_PSEGMENT->callbacks_on_commit_and_abort[0]));
    assert(tree_is_cleared(STM_PSEGMENT->callbacks_on_commit_and_abort[1]));
    assert(STM_PSEGMENT->objects_pointing_to_nursery == NULL);
    assert(STM_PSEGMENT->large_overflow_objects == NULL);
#ifndef NDEBUG
    /* this should not be used when objects_pointing_to_nursery == NULL */
    STM_PSEGMENT->modified_old_objects_markers_num_old = 99999999999999999L;
#endif

    check_nursery_at_transaction_start();
}

long stm_start_transaction(stm_thread_local_t *tl)
{
    s_mutex_lock();
#ifdef STM_NO_AUTOMATIC_SETJMP
    long repeat_count = 0;    /* test/support.py */
#else
    long repeat_count = stm_rewind_jmp_setjmp(tl);
#endif
    _stm_start_transaction(tl);
    return repeat_count;
}

void stm_start_inevitable_transaction(stm_thread_local_t *tl)
{
    /* used to be more efficient, starting directly an inevitable transaction,
       but there is no real point any more, I believe */
    stm_start_transaction(tl);
    stm_become_inevitable(tl, "start_inevitable_transaction");
}


/************************************************************/


static bool detect_write_read_conflicts(void)
{
    /* Detect conflicts of the form: we want to commit a write to an object,
       but the same object was also read in a different thread.
    */
    long i;
    for (i = 1; i <= NB_SEGMENTS; i++) {

        if (i == STM_SEGMENT->segment_num)
            continue;

        if (get_priv_segment(i)->transaction_state == TS_NONE)
            continue;    /* no need to check */

        if (is_aborting_now(i))
            continue;    /* no need to check: is pending immediate abort */

        char *remote_base = get_segment_base(i);
        uint8_t remote_version = get_segment(i)->transaction_read_version;

        LIST_FOREACH_R(
            STM_PSEGMENT->modified_old_objects,
            object_t * /*item*/,
            ({
                if (was_read_remote(remote_base, item, remote_version)) {
                    /* A write-read conflict! */
                    dprintf(("write-read conflict on %p, our seg: %d, other: %ld\n",
                             item, STM_SEGMENT->segment_num, i));
                    if (write_read_contention_management(i, item)) {
                        /* If we reach this point, we didn't abort, but we
                           had to wait for the other thread to commit.  If we
                           did, then we have to restart committing from our call
                           to synchronize_all_threads(). */
                        return true;
                    }
                    /* we aborted the other transaction without waiting, so
                       we can just break out of this loop on
                       modified_old_objects and continue with the next
                       segment */
                    break;
                }
            }));
    }

    return false;
}

static void copy_object_to_shared(object_t *obj, int source_segment_num)
{
    /* Only used by major GC.  XXX There is a lot of code duplication
       with synchronize_object_now() but I don't completely see how to
       improve...
    */
    assert(!_is_young(obj));

    char *segment_base = get_segment_base(source_segment_num);
    uintptr_t start = (uintptr_t)obj;
    uintptr_t first_page = start / 4096UL;
    struct object_s *realobj = (struct object_s *)
        REAL_ADDRESS(segment_base, obj);

    if (realobj->stm_flags & GCFLAG_SMALL_UNIFORM) {
        abort();//XXX WRITE THE FAST CASE
    }
    else {
        ssize_t obj_size = stmcb_size_rounded_up(realobj);
        assert(obj_size >= 16);
        uintptr_t end = start + obj_size;
        uintptr_t last_page = (end - 1) / 4096UL;

        for (; first_page <= last_page; first_page++) {

            /* Copy the object into the shared page, if needed */
            if (is_private_page(source_segment_num, first_page)) {

                uintptr_t copy_size;
                if (first_page == last_page) {
                    /* this is the final fragment */
                    copy_size = end - start;
                }
                else {
                    /* this is a non-final fragment, going up to the
                       page's end */
                    copy_size = 4096 - (start & 4095);
                }
                /* double-check that the result fits in one page */
                assert(copy_size > 0);
                assert(copy_size + (start & 4095) <= 4096);

                char *src = REAL_ADDRESS(segment_base, start);
                char *dst = REAL_ADDRESS(stm_object_pages, start);
                if (copy_size == 4096)
                    pagecopy(dst, src);
                else
                    memcpy(dst, src, copy_size);
            }

            start = (start + 4096) & ~4095;
        }
    }
}

static void _page_wise_synchronize_object_now(object_t *obj)
{
    uintptr_t start = (uintptr_t)obj;
    uintptr_t first_page = start / 4096UL;

    char *realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    ssize_t obj_size = stmcb_size_rounded_up((struct object_s *)realobj);
    assert(obj_size >= 16);
    uintptr_t end = start + obj_size;
    uintptr_t last_page = (end - 1) / 4096UL;
    long i, myself = STM_SEGMENT->segment_num;

    for (; first_page <= last_page; first_page++) {

        uintptr_t copy_size;
        if (first_page == last_page) {
            /* this is the final fragment */
            copy_size = end - start;
        }
        else {
            /* this is a non-final fragment, going up to the
               page's end */
            copy_size = 4096 - (start & 4095);
        }
        /* double-check that the result fits in one page */
        assert(copy_size > 0);
        assert(copy_size + (start & 4095) <= 4096);

        /* First copy the object into the shared page, if needed */
        char *src = REAL_ADDRESS(STM_SEGMENT->segment_base, start);
        char *dst = REAL_ADDRESS(stm_object_pages, start);
        if (is_private_page(myself, first_page)) {
            if (copy_size == 4096)
                pagecopy(dst, src);
            else
                memcpy(dst, src, copy_size);
        }
        else {
            assert(memcmp(dst, src, copy_size) == 0);  /* same page */
        }

        for (i = 1; i <= NB_SEGMENTS; i++) {
            if (i == myself)
                continue;

            /* src = REAL_ADDRESS(stm_object_pages, start); */
            dst = REAL_ADDRESS(get_segment_base(i), start);
            if (is_private_page(i, first_page)) {
                /* The page is a private page.  We need to diffuse this
                   fragment of object from the shared page to this private
                   page. */
                if (copy_size == 4096)
                    pagecopy(dst, src);
                else
                    memcpy(dst, src, copy_size);
            }
            else {
                assert(!memcmp(dst, src, copy_size));  /* same page */
            }
        }

        start = (start + 4096) & ~4095;
    }
}

static inline bool _has_private_page_in_range(
    long seg_num, uintptr_t start, uintptr_t size)
{
    uintptr_t first_page = start / 4096UL;
    uintptr_t last_page = (start + size) / 4096UL;
    for (; first_page <= last_page; first_page++)
        if (is_private_page(seg_num, first_page))
            return true;
    return false;
}

static void _card_wise_synchronize_object_now(object_t *obj)
{
    assert(obj_should_use_cards(obj));
    assert(!(obj->stm_flags & GCFLAG_CARDS_SET));
    assert(!IS_OVERFLOW_OBJ(STM_PSEGMENT, obj));

    uintptr_t offset_itemsize[2];
    struct object_s *realobj = (struct object_s *)REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    size_t obj_size = stmcb_size_rounded_up(realobj);
    assert(obj_size >= 32);
    stmcb_get_card_base_itemsize(realobj, offset_itemsize);
    size_t real_idx_count = (obj_size - offset_itemsize[0]) / offset_itemsize[1];

    uintptr_t first_card_index = get_write_lock_idx((uintptr_t)obj);
    uintptr_t card_index = 1;
    uintptr_t last_card_index = get_index_to_card_index(real_idx_count - 1); /* max valid index */
    long i, myself = STM_SEGMENT->segment_num;

    /* simple heuristic to check if probably the whole object is
       marked anyway so we should do page-wise synchronize */
    if (write_locks[first_card_index + 1] == CARD_MARKED_OLD
        && write_locks[first_card_index + last_card_index] == CARD_MARKED_OLD
        && write_locks[first_card_index + (last_card_index >> 1) + 1] == CARD_MARKED_OLD) {

        dprintf(("card_wise_sync assumes %p,size:%lu is fully marked\n", obj, obj_size));
        _reset_object_cards(get_priv_segment(STM_SEGMENT->segment_num),
                            obj, CARD_CLEAR, false);
        _page_wise_synchronize_object_now(obj);
        return;
    }

    dprintf(("card_wise_sync syncs %p,size:%lu card-wise\n", obj, obj_size));

    /* Combine multiple marked cards and do a memcpy for them. We don't
       try yet to use page_copy() or otherwise take into account privatization
       of pages (except _has_private_page_in_range) */
    bool all_cards_were_cleared = true;

    uintptr_t start_card_index = -1;
    while (card_index <= last_card_index) {
        uintptr_t card_lock_idx = first_card_index + card_index;
        uint8_t card_value = write_locks[card_lock_idx];

        if (card_value == CARD_MARKED_OLD) {
            write_locks[card_lock_idx] = CARD_CLEAR;

            if (start_card_index == -1) {   /* first marked card */
                start_card_index = card_index;
                /* start = (uintptr_t)obj + stmcb_index_to_byte_offset( */
                /*     realobj, get_card_index_to_index(card_index)); */
                if (all_cards_were_cleared) {
                    all_cards_were_cleared = false;
                }
            }
        }
        else {
            OPT_ASSERT(card_value == CARD_CLEAR);
        }

        if (start_card_index != -1                    /* something to copy */
            && (card_value != CARD_MARKED_OLD         /* found non-marked card */
                || card_index == last_card_index)) {  /* this is the last card */
            /* do the copying: */
            uintptr_t start, copy_size;
            uintptr_t next_card_offset;
            uintptr_t start_card_offset;
            uintptr_t next_card_index = card_index;

            if (card_value == CARD_MARKED_OLD) {
                /* card_index is the last card of the object, but we need
                   to go one further to get the right offset */
                next_card_index++;
            }

            start_card_offset = offset_itemsize[0] +
                get_card_index_to_index(start_card_index) * offset_itemsize[1];

            next_card_offset = offset_itemsize[0] +
                get_card_index_to_index(next_card_index) * offset_itemsize[1];

            if (next_card_offset > obj_size)
                next_card_offset = obj_size;

            start = (uintptr_t)obj + start_card_offset;
            copy_size = next_card_offset - start_card_offset;
            OPT_ASSERT(copy_size > 0);

            /* dprintf(("copy %lu bytes\n", copy_size)); */

            /* since we have marked cards, at least one page here must be private */
            assert(_has_private_page_in_range(myself, start, copy_size));

            /* copy to shared segment: */
            char *src = REAL_ADDRESS(STM_SEGMENT->segment_base, start);
            char *dst = REAL_ADDRESS(stm_object_pages, start);
            memcpy(dst, src, copy_size);

            /* copy to other segments */
            for (i = 1; i <= NB_SEGMENTS; i++) {
                if (i == myself)
                    continue;
                if (!_has_private_page_in_range(i, start, copy_size))
                    continue;
                /* src = REAL_ADDRESS(stm_object_pages, start); */
                dst = REAL_ADDRESS(get_segment_base(i), start);
                memcpy(dst, src, copy_size);
            }

            start_card_index = -1;
        }

        card_index++;
    }

    if (all_cards_were_cleared) {
        /* well, seems like we never called stm_write_card() on it, so actually
           we need to fall back to synchronize the whole object */
        _page_wise_synchronize_object_now(obj);
        return;
    }

#ifndef NDEBUG
    char *src = REAL_ADDRESS(stm_object_pages, (uintptr_t)obj);
    char *dst;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        dst = REAL_ADDRESS(get_segment_base(i), (uintptr_t)obj);
        assert(memcmp(dst, src, obj_size) == 0);
    }
#endif
}


static void synchronize_object_now(object_t *obj, bool ignore_cards)
{
    /* Copy around the version of 'obj' that lives in our own segment.
       It is first copied into the shared pages, and then into other
       segments' own private pages.

       Must be called with the privatization lock acquired.
    */
    assert(!_is_young(obj));
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);
    assert(STM_PSEGMENT->privatization_lock == 1);

    if (obj->stm_flags & GCFLAG_SMALL_UNIFORM) {
        assert(!(obj->stm_flags & GCFLAG_CARDS_SET));
        abort();//XXX WRITE THE FAST CASE
    } else if (ignore_cards || !obj_should_use_cards(obj)) {
        _page_wise_synchronize_object_now(obj);
    } else {
        _card_wise_synchronize_object_now(obj);
    }

    _cards_cleared_in_object(get_priv_segment(STM_SEGMENT->segment_num), obj);
}

static void push_overflow_objects_from_privatized_pages(void)
{
    if (STM_PSEGMENT->large_overflow_objects == NULL)
        return;

    acquire_privatization_lock();
    LIST_FOREACH_R(STM_PSEGMENT->large_overflow_objects, object_t *,
                   synchronize_object_now(item, true /*ignore_cards*/));
    release_privatization_lock();
}

static void push_modified_to_other_segments(void)
{
    acquire_privatization_lock();
    LIST_FOREACH_R(
        STM_PSEGMENT->modified_old_objects,
        object_t * /*item*/,
        ({
            /* clear the write-lock (note that this runs with all other
               threads paused, so no need to be careful about ordering) */
            uintptr_t lock_idx = (((uintptr_t)item) >> 4) - WRITELOCK_START;
            assert(lock_idx < sizeof(write_locks));
            assert(write_locks[lock_idx] == STM_PSEGMENT->write_lock_num);
            write_locks[lock_idx] = 0;

            /* the WRITE_BARRIER flag should have been set again by
               minor_collection() */
            assert((item->stm_flags & GCFLAG_WRITE_BARRIER) != 0);

            /* copy the object to the shared page, and to the other
               private pages as needed */
            synchronize_object_now(item, false); /* don't ignore_cards */
        }));
    release_privatization_lock();

    list_clear(STM_PSEGMENT->modified_old_objects);
    list_clear(STM_PSEGMENT->modified_old_objects_markers);
}

static void _finish_transaction(enum stm_event_e event)
{
    STM_PSEGMENT->safe_point = SP_NO_TRANSACTION;
    STM_PSEGMENT->transaction_state = TS_NONE;

    /* marker_inev is not needed anymore */
    STM_PSEGMENT->marker_inev.object = NULL;

    /* reset these lists to NULL for the next transaction */
    _verify_cards_cleared_in_all_lists(get_priv_segment(STM_SEGMENT->segment_num));
    LIST_FREE(STM_PSEGMENT->objects_pointing_to_nursery);
    list_clear(STM_PSEGMENT->old_objects_with_cards);
    LIST_FREE(STM_PSEGMENT->large_overflow_objects);

    stm_thread_local_t *tl = STM_SEGMENT->running_thread;
    timing_event(tl, event);

    release_thread_segment(tl);
    /* cannot access STM_SEGMENT or STM_PSEGMENT from here ! */
}

void stm_commit_transaction(void)
{
    assert(!_has_mutex());
    assert(STM_PSEGMENT->safe_point == SP_RUNNING);
    assert(STM_PSEGMENT->running_pthread == pthread_self());

    minor_collection(/*commit=*/ true);

    /* synchronize overflow objects living in privatized pages */
    push_overflow_objects_from_privatized_pages();

    s_mutex_lock();

 restart:
    /* force all other threads to be paused.  They will unpause
       automatically when we are done here, i.e. at mutex_unlock().
       Important: we should not call cond_wait() in the meantime. */
    synchronize_all_threads(STOP_OTHERS_UNTIL_MUTEX_UNLOCK);

    /* detect conflicts */
    if (detect_write_read_conflicts())
        goto restart;

    /* cannot abort any more from here */
    dprintf(("commit_transaction\n"));

    assert(STM_SEGMENT->nursery_end == NURSERY_END);
    stm_rewind_jmp_forget(STM_SEGMENT->running_thread);

    /* if a major collection is required, do it here */
    if (is_major_collection_requested()) {
        timing_event(STM_SEGMENT->running_thread, STM_GC_MAJOR_START);
        major_collection_now_at_safe_point();
        timing_event(STM_SEGMENT->running_thread, STM_GC_MAJOR_DONE);
    }

    /* synchronize modified old objects to other threads */
    push_modified_to_other_segments();
    _verify_cards_cleared_in_all_lists(get_priv_segment(STM_SEGMENT->segment_num));

    /* update 'overflow_number' if needed */
    if (STM_PSEGMENT->overflow_number_has_been_used) {
        highest_overflow_number += GCFLAG_OVERFLOW_NUMBER_bit0;
        assert(highest_overflow_number !=        /* XXX else, overflow! */
               (uint32_t)-GCFLAG_OVERFLOW_NUMBER_bit0);
        STM_PSEGMENT->overflow_number = highest_overflow_number;
        STM_PSEGMENT->overflow_number_has_been_used = false;
    }

    invoke_and_clear_user_callbacks(0);   /* for commit */

    /* send what is hopefully the correct signals */
    if (STM_PSEGMENT->transaction_state == TS_INEVITABLE) {
        /* wake up one thread in wait_for_end_of_inevitable_transaction() */
        cond_signal(C_INEVITABLE);
        if (globally_unique_transaction)
            committed_globally_unique_transaction();
    }

    /* done */
    _finish_transaction(STM_TRANSACTION_COMMIT);
    /* cannot access STM_SEGMENT or STM_PSEGMENT from here ! */

    s_mutex_unlock();
}

void stm_abort_transaction(void)
{
    s_mutex_lock();
    abort_with_mutex();
}

static void
reset_modified_from_other_segments(int segment_num)
{
    /* pull the right versions from segment 0 in order
       to reset our pages as part of an abort.

       Note that this function is also sometimes called from
       contention.c to clean up the state of a different thread,
       when we would really like it to be aborted now and it is
       suspended at a safe-point.
    */
    struct stm_priv_segment_info_s *pseg = get_priv_segment(segment_num);
    char *local_base = get_segment_base(segment_num);
    char *remote_base = get_segment_base(0);

    LIST_FOREACH_R(
        pseg->modified_old_objects,
        object_t * /*item*/,
        ({
            /* memcpy in the opposite direction than
               push_modified_to_other_segments() */
            char *src = REAL_ADDRESS(remote_base, item);
            char *dst = REAL_ADDRESS(local_base, item);
            ssize_t size = stmcb_size_rounded_up((struct object_s *)src);
            memcpy(dst, src, size);

            if (obj_should_use_cards(item))
                _reset_object_cards(pseg, item, CARD_CLEAR, false);

            /* objects in 'modified_old_objects' usually have the
               WRITE_BARRIER flag, unless they have been modified
               recently.  Ignore the old flag; after copying from the
               other segment, we should have the flag. */
            assert(((struct object_s *)dst)->stm_flags & GCFLAG_WRITE_BARRIER);

            /* write all changes to the object before we release the
               write lock below.  This is needed because we need to
               ensure that if the write lock is not set, another thread
               can get it and then change 'src' in parallel.  The
               write_fence() ensures in particular that 'src' has been
               fully read before we release the lock: reading it
               is necessary to write 'dst'. */
            write_fence();

            /* clear the write-lock */
            uintptr_t lock_idx = (((uintptr_t)item) >> 4) - WRITELOCK_START;
            assert(lock_idx < sizeof(write_locks));
            assert(write_locks[lock_idx] == pseg->write_lock_num);
            write_locks[lock_idx] = 0;
        }));

    list_clear(pseg->modified_old_objects);
    list_clear(pseg->modified_old_objects_markers);
}

static void abort_data_structures_from_segment_num(int segment_num)
{
#pragma push_macro("STM_PSEGMENT")
#pragma push_macro("STM_SEGMENT")
#undef STM_PSEGMENT
#undef STM_SEGMENT
    /* This function clears the content of the given segment undergoing
       an abort.  It is called from abort_with_mutex(), but also sometimes
       from other threads that figure out that this segment should abort.
       In the latter case, make sure that this segment is currently at
       a safe point (not SP_RUNNING).  Note that in such cases this
       function is called more than once for the same segment, but it
       should not matter.
    */
    struct stm_priv_segment_info_s *pseg = get_priv_segment(segment_num);

    switch (pseg->transaction_state) {
    case TS_REGULAR:
        break;
    case TS_INEVITABLE:
        stm_fatalerror("abort: transaction_state == TS_INEVITABLE");
    default:
        stm_fatalerror("abort: bad transaction_state == %d",
                       (int)pseg->transaction_state);
    }

    /* throw away the content of the nursery */
    long bytes_in_nursery = throw_away_nursery(pseg);

    /* modified_old_objects' cards get cleared in
       reset_modified_from_other_segments. Objs in old_objs_with_cards but not
       in modified_old_objs are overflow objects and handled here: */
    if (pseg->large_overflow_objects != NULL) {
        /* some overflow objects may have cards when aborting, clear them too */
        LIST_FOREACH_R(pseg->large_overflow_objects, object_t * /*item*/,
            {
                struct object_s *realobj = (struct object_s *)
                    REAL_ADDRESS(pseg->pub.segment_base, item);

                if (realobj->stm_flags & GCFLAG_CARDS_SET) {
                    /* CARDS_SET is enough since other HAS_CARDS objs
                       are already cleared */
                    _reset_object_cards(pseg, item, CARD_CLEAR, false);
                }
            });
    }

    /* reset all the modified objects (incl. re-adding GCFLAG_WRITE_BARRIER) */
    reset_modified_from_other_segments(segment_num);
    _verify_cards_cleared_in_all_lists(pseg);

    /* reset tl->shadowstack and thread_local_obj to their original
       value before the transaction start.  Also restore the content
       of the shadowstack here. */
    stm_thread_local_t *tl = pseg->pub.running_thread;
#ifdef STM_NO_AUTOMATIC_SETJMP
    /* In tests, we don't save and restore the shadowstack correctly.
       Be sure to not change items below shadowstack_at_start_of_transaction.
       There is no such restrictions in non-Python-based tests. */
    assert(tl->shadowstack >= pseg->shadowstack_at_start_of_transaction);
    tl->shadowstack = pseg->shadowstack_at_start_of_transaction;
#else
    /* NB. careful, this function might be called more than once to
       abort a given segment.  Make sure that
       stm_rewind_jmp_restore_shadowstack() is idempotent. */
    /* we need to do this here and not directly in rewind_longjmp() because
       that is called when we already released everything (safe point)
       and a concurrent major GC could mess things up. */
    if (tl->shadowstack != NULL)
        stm_rewind_jmp_restore_shadowstack(tl);
    assert(tl->shadowstack == pseg->shadowstack_at_start_of_transaction);
#endif
    tl->thread_local_obj = pseg->threadlocal_at_start_of_transaction;
    tl->last_abort__bytes_in_nursery = bytes_in_nursery;

    /* reset these lists to NULL too on abort */
    LIST_FREE(pseg->objects_pointing_to_nursery);
    list_clear(pseg->old_objects_with_cards);
    LIST_FREE(pseg->large_overflow_objects);
    list_clear(pseg->young_weakrefs);
#pragma pop_macro("STM_SEGMENT")
#pragma pop_macro("STM_PSEGMENT")
}

#ifdef STM_NO_AUTOMATIC_SETJMP
void _test_run_abort(stm_thread_local_t *tl) __attribute__((noreturn));
int stm_is_inevitable(void)
{
    switch (STM_PSEGMENT->transaction_state) {
    case TS_REGULAR: return 0;
    case TS_INEVITABLE: return 1;
    default: abort();
    }
}
#endif

static stm_thread_local_t *abort_with_mutex_no_longjmp(void)
{
    assert(_has_mutex());
    dprintf(("~~~ ABORT\n"));

    assert(STM_PSEGMENT->running_pthread == pthread_self());

    abort_data_structures_from_segment_num(STM_SEGMENT->segment_num);

    stm_thread_local_t *tl = STM_SEGMENT->running_thread;

    /* clear memory registered on the thread-local */
    if (tl->mem_clear_on_abort)
        memset(tl->mem_clear_on_abort, 0, tl->mem_bytes_to_clear_on_abort);

    /* invoke the callbacks */
    invoke_and_clear_user_callbacks(1);   /* for abort */

    if (is_abort(STM_SEGMENT->nursery_end)) {
        /* done aborting */
        STM_SEGMENT->nursery_end = pause_signalled ? NSE_SIGPAUSE
                                                   : NURSERY_END;
    }

    _finish_transaction(STM_TRANSACTION_ABORT);
    /* cannot access STM_SEGMENT or STM_PSEGMENT from here ! */

    /* Broadcast C_ABORTED to wake up contention.c */
    cond_broadcast(C_ABORTED);

    return tl;
}

static void abort_with_mutex(void)
{
    stm_thread_local_t *tl = abort_with_mutex_no_longjmp();
    s_mutex_unlock();

    /* It seems to be a good idea, at least in some examples, to sleep
       one microsecond here before retrying.  Otherwise, what was
       observed is that the transaction very often restarts too quickly
       for contention.c to react, and before it can do anything, we have
       again recreated in this thread a similar situation to the one
       that caused contention.  Anyway, usleep'ing in case of abort
       doesn't seem like a very bad idea.  If there are more threads
       than segments, it should also make sure another thread gets the
       segment next.
    */
    usleep(1);

#ifdef STM_NO_AUTOMATIC_SETJMP
    _test_run_abort(tl);
#else
    s_mutex_lock();
    stm_rewind_jmp_longjmp(tl);
#endif
}

void _stm_become_inevitable(const char *msg)
{
    s_mutex_lock();
    enter_safe_point_if_requested();

    if (STM_PSEGMENT->transaction_state == TS_REGULAR) {
        dprintf(("become_inevitable: %s\n", msg));

        timing_fetch_inev();
        wait_for_end_of_inevitable_transaction();
        STM_PSEGMENT->transaction_state = TS_INEVITABLE;
        stm_rewind_jmp_forget(STM_SEGMENT->running_thread);
        invoke_and_clear_user_callbacks(0);   /* for commit */
    }
    else {
        assert(STM_PSEGMENT->transaction_state == TS_INEVITABLE);
    }

    s_mutex_unlock();
}

void stm_become_globally_unique_transaction(stm_thread_local_t *tl,
                                            const char *msg)
{
    stm_become_inevitable(tl, msg);   /* may still abort */

    s_mutex_lock();
    synchronize_all_threads(STOP_OTHERS_AND_BECOME_GLOBALLY_UNIQUE);
    s_mutex_unlock();
}
