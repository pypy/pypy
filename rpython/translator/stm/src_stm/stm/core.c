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
            int _i;                                             \
            for (_i = 1; _i <= NB_SEGMENTS; _i++)               \
                spinlock_acquire(lock_pages_privatizing[_i]);   \
            if (!(condition))                                   \
                stm_fatalerror("fails: " #condition);           \
            for (_i = 1; _i <= NB_SEGMENTS; _i++)               \
                spinlock_release(lock_pages_privatizing[_i]);   \
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

void _stm_write_slowpath(object_t *obj)
{
    assert(_seems_to_be_running_transaction());
    assert(!_is_young(obj));
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);

    /* is this an object from the same transaction, outside the nursery? */
    if ((obj->stm_flags & -GCFLAG_OVERFLOW_NUMBER_bit0) ==
            STM_PSEGMENT->overflow_number) {

        dprintf_test(("write_slowpath %p -> ovf obj_to_nurs\n", obj));
        obj->stm_flags &= ~GCFLAG_WRITE_BARRIER;
        assert(STM_PSEGMENT->objects_pointing_to_nursery != NULL);
        LIST_APPEND(STM_PSEGMENT->objects_pointing_to_nursery, obj);
        return;
    }

    /* do a read-barrier now.  Note that this must occur before the
       safepoints that may be issued in write_write_contention_management(). */
    stm_read(obj);

    /* XXX XXX XXX make the logic of write-locking objects optional! */

    /* claim the write-lock for this object.  In case we're running the
       same transaction since a long while, the object can be already in
       'modified_old_objects' (but, because it had GCFLAG_WRITE_BARRIER,
       not in 'objects_pointing_to_nursery').  We'll detect this case
       by finding that we already own the write-lock. */
    uintptr_t lock_idx = (((uintptr_t)obj) >> 4) - WRITELOCK_START;
    uint8_t lock_num = STM_PSEGMENT->write_lock_num;
    assert(lock_idx < sizeof(write_locks));
 retry:
    if (write_locks[lock_idx] == 0) {
        if (UNLIKELY(!__sync_bool_compare_and_swap(&write_locks[lock_idx],
                                                   0, lock_num)))
            goto retry;

        dprintf_test(("write_slowpath %p -> mod_old\n", obj));

        /* First change to this old object from this transaction.
           Add it to the list 'modified_old_objects'. */
        LIST_APPEND(STM_PSEGMENT->modified_old_objects, obj);

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

            /* that's the page *following* the last page with the object */
            end_page = (((uintptr_t)obj) + obj_size + 4095) / 4096UL;

            for (i = first_page; i < end_page; i++) {
                page_privatize(i);
            }
        }
    }
    else if (write_locks[lock_idx] == lock_num) {
        OPT_ASSERT(STM_PSEGMENT->objects_pointing_to_nursery != NULL);
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
        write_write_contention_management(lock_idx);
        goto retry;
    }

    /* A common case for write_locks[] that was either 0 or lock_num:
       we need to add the object to 'objects_pointing_to_nursery'
       if there is such a list. */
    if (STM_PSEGMENT->objects_pointing_to_nursery != NULL) {
        dprintf_test(("write_slowpath %p -> old obj_to_nurs\n", obj));
        LIST_APPEND(STM_PSEGMENT->objects_pointing_to_nursery, obj);
    }

    /* check that we really have a private page */
    assert(is_private_page(STM_SEGMENT->segment_num,
                           ((uintptr_t)obj) / 4096));

    /* check that so far all copies of the object have the flag */
    check_flag_write_barrier(obj);

    /* remove GCFLAG_WRITE_BARRIER, but only if we succeeded in
       getting the write-lock */
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);
    obj->stm_flags &= ~GCFLAG_WRITE_BARRIER;

    /* for sanity, check again that all other segment copies of this
       object still have the flag (so privatization worked) */
    check_flag_write_barrier(obj);
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

void _stm_start_transaction(stm_thread_local_t *tl, stm_jmpbuf_t *jmpbuf)
{
    assert(!_stm_in_transaction(tl));

    s_mutex_lock();

  retry:
    if (jmpbuf == NULL) {
        wait_for_end_of_inevitable_transaction(tl);
    }

    if (!acquire_thread_segment(tl))
        goto retry;
    /* GS invalid before this point! */

    assert(STM_PSEGMENT->safe_point == SP_NO_TRANSACTION);
    assert(STM_PSEGMENT->transaction_state == TS_NONE);
    change_timing_state(STM_TIME_RUN_CURRENT);
    STM_PSEGMENT->start_time = tl->_timing_cur_start;
    STM_PSEGMENT->safe_point = SP_RUNNING;
    STM_PSEGMENT->transaction_state = (jmpbuf != NULL ? TS_REGULAR
                                                      : TS_INEVITABLE);
    STM_SEGMENT->jmpbuf_ptr = jmpbuf;
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
    assert(list_is_empty(STM_PSEGMENT->young_weakrefs));
    assert(tree_is_cleared(STM_PSEGMENT->young_outside_nursery));
    assert(tree_is_cleared(STM_PSEGMENT->nursery_objects_shadows));
    assert(tree_is_cleared(STM_PSEGMENT->callbacks_on_abort));
    assert(STM_PSEGMENT->objects_pointing_to_nursery == NULL);
    assert(STM_PSEGMENT->large_overflow_objects == NULL);

    check_nursery_at_transaction_start();
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
                    write_read_contention_management(i);

                    /* If we reach this point, we didn't abort, but maybe we
                       had to wait for the other thread to commit.  If we
                       did, then we have to restart committing from our call
                       to synchronize_all_threads(). */
                    return true;
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

static void synchronize_object_now(object_t *obj)
{
    /* Copy around the version of 'obj' that lives in our own segment.
       It is first copied into the shared pages, and then into other
       segments' own private pages.
    */
    assert(!_is_young(obj));
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);

    uintptr_t start = (uintptr_t)obj;
    uintptr_t first_page = start / 4096UL;

    if (obj->stm_flags & GCFLAG_SMALL_UNIFORM) {
        abort();//XXX WRITE THE FAST CASE
    }
    else {
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
                EVENTUALLY(memcmp(dst, src, copy_size) == 0);  /* same page */
            }

            /* Do a full memory barrier.  We must make sure that other
               CPUs see the changes we did to the shared page ("S",
               above) before we check the other segments below with
               is_private_page().  Otherwise, we risk the following:
               this CPU writes "S" but the writes are not visible yet;
               then it checks is_private_page() and gets false, and does
               nothing more; just afterwards another CPU sets its own
               private_page bit and copies the page; but it risks doing
               so before seeing the "S" writes.

               XXX what is the cost of this?  If it's high, then we
               should reorganize the code so that we buffer the second
               parts and do them by bunch of N, after just one call to
               __sync_synchronize()...
            */
            __sync_synchronize();

            for (i = 1; i <= NB_SEGMENTS; i++) {
                if (i == myself)
                    continue;

                src = REAL_ADDRESS(stm_object_pages, start);
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
                    EVENTUALLY(!memcmp(dst, src, copy_size));  /* same page */
                }
            }

            start = (start + 4096) & ~4095;
        }
    }
}

static void push_overflow_objects_from_privatized_pages(void)
{
    if (STM_PSEGMENT->large_overflow_objects == NULL)
        return;

    LIST_FOREACH_R(STM_PSEGMENT->large_overflow_objects, object_t *,
                   synchronize_object_now(item));
}

static void push_modified_to_other_segments(void)
{
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
            synchronize_object_now(item);
        }));

    list_clear(STM_PSEGMENT->modified_old_objects);
}

static void _finish_transaction(int attribute_to)
{
    STM_PSEGMENT->safe_point = SP_NO_TRANSACTION;
    STM_PSEGMENT->transaction_state = TS_NONE;

    /* reset these lists to NULL for the next transaction */
    LIST_FREE(STM_PSEGMENT->objects_pointing_to_nursery);
    LIST_FREE(STM_PSEGMENT->large_overflow_objects);

    timing_end_transaction(attribute_to);

    stm_thread_local_t *tl = STM_SEGMENT->running_thread;
    release_thread_segment(tl);
    /* cannot access STM_SEGMENT or STM_PSEGMENT from here ! */
}

void stm_commit_transaction(void)
{
    assert(!_has_mutex());
    assert(STM_PSEGMENT->safe_point == SP_RUNNING);
    assert(STM_PSEGMENT->running_pthread == pthread_self());

    minor_collection(/*commit=*/ true);

    /* the call to minor_collection() above leaves us with
       STM_TIME_BOOKKEEPING */

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
    STM_SEGMENT->jmpbuf_ptr = NULL;

    /* if a major collection is required, do it here */
    if (is_major_collection_requested())
        major_collection_now_at_safe_point();

    /* synchronize overflow objects living in privatized pages */
    push_overflow_objects_from_privatized_pages();

    /* synchronize modified old objects to other threads */
    push_modified_to_other_segments();

    /* update 'overflow_number' if needed */
    if (STM_PSEGMENT->overflow_number_has_been_used) {
        highest_overflow_number += GCFLAG_OVERFLOW_NUMBER_bit0;
        assert(highest_overflow_number !=        /* XXX else, overflow! */
               (uint32_t)-GCFLAG_OVERFLOW_NUMBER_bit0);
        STM_PSEGMENT->overflow_number = highest_overflow_number;
        STM_PSEGMENT->overflow_number_has_been_used = false;
    }

    clear_callbacks_on_abort();

    /* send what is hopefully the correct signals */
    if (STM_PSEGMENT->transaction_state == TS_INEVITABLE) {
        /* wake up one thread in wait_for_end_of_inevitable_transaction() */
        cond_signal(C_INEVITABLE);
        if (globally_unique_transaction)
            committed_globally_unique_transaction();
    }

    /* done */
    _finish_transaction(STM_TIME_RUN_COMMITTED);
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

            /* objects in 'modified_old_objects' usually have the
               WRITE_BARRIER flag, unless they have been modified
               recently.  Ignore the old flag; after copying from the
               other segment, we should have the flag. */
            assert(item->stm_flags & GCFLAG_WRITE_BARRIER);

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
}

static void abort_data_structures_from_segment_num(int segment_num)
{
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

    /* reset all the modified objects (incl. re-adding GCFLAG_WRITE_BARRIER) */
    reset_modified_from_other_segments(segment_num);

    /* reset the tl->shadowstack and thread_local_obj to their original
       value before the transaction start */
    stm_thread_local_t *tl = pseg->pub.running_thread;
    assert(tl->shadowstack >= pseg->shadowstack_at_start_of_transaction);
    tl->shadowstack = pseg->shadowstack_at_start_of_transaction;
    tl->thread_local_obj = pseg->threadlocal_at_start_of_transaction;
    tl->last_abort__bytes_in_nursery = bytes_in_nursery;

    /* reset these lists to NULL too on abort */
    LIST_FREE(pseg->objects_pointing_to_nursery);
    LIST_FREE(pseg->large_overflow_objects);
    list_clear(pseg->young_weakrefs);
}

static void abort_with_mutex(void)
{
    assert(_has_mutex());
    dprintf(("~~~ ABORT\n"));

    assert(STM_PSEGMENT->running_pthread == pthread_self());

    abort_data_structures_from_segment_num(STM_SEGMENT->segment_num);

    stm_jmpbuf_t *jmpbuf_ptr = STM_SEGMENT->jmpbuf_ptr;

    /* clear memory registered on the thread-local */
    stm_thread_local_t *tl = STM_SEGMENT->running_thread;
    if (tl->mem_clear_on_abort)
        memset(tl->mem_clear_on_abort, 0, tl->mem_bytes_to_clear_on_abort);

    /* invoke the callbacks */
    invoke_and_clear_callbacks_on_abort();

    int attribute_to = STM_TIME_RUN_ABORTED_OTHER;

    if (is_abort(STM_SEGMENT->nursery_end)) {
        /* done aborting */
        attribute_to = STM_SEGMENT->nursery_end;
        STM_SEGMENT->nursery_end = pause_signalled ? NSE_SIGPAUSE
                                                   : NURSERY_END;
    }

    _finish_transaction(attribute_to);
    /* cannot access STM_SEGMENT or STM_PSEGMENT from here ! */

    /* Broadcast C_ABORTED to wake up contention.c */
    cond_broadcast(C_ABORTED);

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

    assert(jmpbuf_ptr != NULL);
    assert(jmpbuf_ptr != (stm_jmpbuf_t *)-1);    /* for tests only */
    __builtin_longjmp(*jmpbuf_ptr, 1);
}

void _stm_become_inevitable(const char *msg)
{
    s_mutex_lock();
    enter_safe_point_if_requested();

    if (STM_PSEGMENT->transaction_state == TS_REGULAR) {
        dprintf(("become_inevitable: %s\n", msg));

        wait_for_end_of_inevitable_transaction(NULL);
        STM_PSEGMENT->transaction_state = TS_INEVITABLE;
        STM_SEGMENT->jmpbuf_ptr = NULL;
        clear_callbacks_on_abort();
    }
    else {
        assert(STM_PSEGMENT->transaction_state == TS_INEVITABLE);
        assert(STM_SEGMENT->jmpbuf_ptr == NULL);
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
