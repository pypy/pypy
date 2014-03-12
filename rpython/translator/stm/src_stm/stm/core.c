/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


static void teardown_core(void)
{
    memset(write_locks, 0, sizeof(write_locks));
}


void _stm_write_slowpath(object_t *obj)
{
    assert(_running_transaction());
    assert(!_is_young(obj));

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
            pages_privatize(first_page, 1, true);
        }
        else {
            char *realobj;
            size_t obj_size;
            uintptr_t end_page;

            /* get the size of the object */
            realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
            obj_size = stmcb_size_rounded_up((struct object_s *)realobj);

            /* that's the page *following* the last page with the object */
            end_page = (((uintptr_t)obj) + obj_size + 4095) / 4096UL;

            pages_privatize(first_page, end_page - first_page, true);
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

    /* add the write-barrier-already-called flag ONLY if we succeeded in
       getting the write-lock */
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);
    obj->stm_flags &= ~GCFLAG_WRITE_BARRIER;

    /* for sanity, check that all other segment copies of this object
       still have the flag */
    long i;
    for (i = 0; i < NB_SEGMENTS; i++) {
        if (i != STM_SEGMENT->segment_num)
            assert(((struct object_s *)REAL_ADDRESS(get_segment_base(i), obj))
                   ->stm_flags & GCFLAG_WRITE_BARRIER);
    }
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
        stm_fatalerror("reset_transaction_read_version: %m\n");
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
        wait_for_end_of_inevitable_transaction(false);
    }

    if (!acquire_thread_segment(tl))
        goto retry;
    /* GS invalid before this point! */

    assert(STM_PSEGMENT->safe_point == SP_NO_TRANSACTION);
    assert(STM_PSEGMENT->transaction_state == TS_NONE);
    STM_PSEGMENT->safe_point = SP_RUNNING;
    STM_PSEGMENT->transaction_state = (jmpbuf != NULL ? TS_REGULAR
                                                      : TS_INEVITABLE);
    STM_SEGMENT->jmpbuf_ptr = jmpbuf;
#ifndef NDEBUG
    STM_PSEGMENT->running_pthread = pthread_self();
#endif
    STM_PSEGMENT->shadowstack_at_start_of_transaction = tl->shadowstack;
    STM_PSEGMENT->threadlocal_at_start_of_transaction = tl->thread_local_obj;

    dprintf(("start_transaction\n"));

    enter_safe_point_if_requested();
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
    assert(tree_is_cleared(STM_PSEGMENT->young_outside_nursery));
    assert(tree_is_cleared(STM_PSEGMENT->nursery_objects_shadows));
    assert(tree_is_cleared(STM_PSEGMENT->callbacks_on_abort));
    assert(STM_PSEGMENT->objects_pointing_to_nursery == NULL);
    assert(STM_PSEGMENT->large_overflow_objects == NULL);

    check_nursery_at_transaction_start();
}


/************************************************************/

#if NB_SEGMENTS != 2
# error "The logic in the functions below only works with two segments"
#endif

static bool detect_write_read_conflicts(void)
{
    long remote_num = 1 - STM_SEGMENT->segment_num;
    char *remote_base = get_segment_base(remote_num);
    uint8_t remote_version = get_segment(remote_num)->transaction_read_version;

    if (get_priv_segment(remote_num)->transaction_state == TS_NONE)
        return false;    /* no need to check */

    if (is_aborting_now(remote_num))
        return false;    /* no need to check: is pending immediate abort */

    LIST_FOREACH_R(
        STM_PSEGMENT->modified_old_objects,
        object_t * /*item*/,
        ({
            if (was_read_remote(remote_base, item, remote_version)) {
                /* A write-read conflict! */
                write_read_contention_management(remote_num);

                /* If we reach this point, we didn't abort, but maybe we
                   had to wait for the other thread to commit.  If we
                   did, then we have to restart committing from our call
                   to synchronize_all_threads(). */
                return true;
            }
        }));

    return false;
}

static void synchronize_overflow_object_now(object_t *obj)
{
    assert(!_is_young(obj));
    assert((obj->stm_flags & GCFLAG_SMALL_UNIFORM) == 0);
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);

    char *realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    ssize_t obj_size = stmcb_size_rounded_up((struct object_s *)realobj);
    assert(obj_size >= 16);
    uintptr_t start = (uintptr_t)obj;
    uintptr_t end = start + obj_size;
    uintptr_t first_page = start / 4096UL;
    uintptr_t last_page = (end - 1) / 4096UL;

    do {
        if (flag_page_private[first_page] != SHARED_PAGE) {
            /* The page is a PRIVATE_PAGE.  We need to diffuse this fragment
               of our object from our own segment to all other segments. */

            uintptr_t copy_size;
            if (first_page == last_page) {
                /* this is the final fragment */
                copy_size = end - start;
            }
            else {
                /* this is a non-final fragment, going up to the page's end */
                copy_size = 4096 - (start & 4095);
            }

            /* double-check that the result fits in one page */
            assert(copy_size > 0);
            assert(copy_size + (start & 4095) <= 4096);

            long i;
            char *src = REAL_ADDRESS(STM_SEGMENT->segment_base, start);
            for (i = 0; i < NB_SEGMENTS; i++) {
                if (i != STM_SEGMENT->segment_num) {
                    char *dst = REAL_ADDRESS(get_segment_base(i), start);
                    memcpy(dst, src, copy_size);
                }
            }
        }

        start = (start + 4096) & ~4095;
    } while (first_page++ < last_page);
}

static void push_overflow_objects_from_privatized_pages(void)
{
    if (STM_PSEGMENT->large_overflow_objects == NULL)
        return;

    LIST_FOREACH_R(STM_PSEGMENT->large_overflow_objects, object_t *,
                   synchronize_overflow_object_now(item));
}

static void push_modified_to_other_segments(void)
{
    long remote_num = 1 - STM_SEGMENT->segment_num;
    char *local_base = STM_SEGMENT->segment_base;
    char *remote_base = get_segment_base(remote_num);
    bool remote_active =
        (get_priv_segment(remote_num)->transaction_state != TS_NONE &&
         get_segment(remote_num)->nursery_end != NSE_SIGABORT);

    LIST_FOREACH_R(
        STM_PSEGMENT->modified_old_objects,
        object_t * /*item*/,
        ({
            if (remote_active) {
                assert(!was_read_remote(remote_base, item,
                    get_segment(remote_num)->transaction_read_version));
            }

            /* clear the write-lock (note that this runs with all other
               threads paused, so no need to be careful about ordering) */
            uintptr_t lock_idx = (((uintptr_t)item) >> 4) - WRITELOCK_START;
            assert(lock_idx < sizeof(write_locks));
            assert(write_locks[lock_idx] == STM_PSEGMENT->write_lock_num);
            write_locks[lock_idx] = 0;

            /* the WRITE_BARRIER flag should have been set again by
               minor_collection() */
            assert((item->stm_flags & GCFLAG_WRITE_BARRIER) != 0);

            /* copy the modified object to the other segment */
            char *src = REAL_ADDRESS(local_base, item);
            char *dst = REAL_ADDRESS(remote_base, item);
            ssize_t size = stmcb_size_rounded_up((struct object_s *)src);
            memcpy(dst, src, size);
        }));

    list_clear(STM_PSEGMENT->modified_old_objects);
}

static void _finish_transaction(void)
{
    STM_PSEGMENT->safe_point = SP_NO_TRANSACTION;
    STM_PSEGMENT->transaction_state = TS_NONE;

    /* reset these lists to NULL for the next transaction */
    LIST_FREE(STM_PSEGMENT->objects_pointing_to_nursery);
    LIST_FREE(STM_PSEGMENT->large_overflow_objects);

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

    s_mutex_lock();

 restart:
    /* force all other threads to be paused.  They will unpause
       automatically when we are done here, i.e. at mutex_unlock().
       Important: we should not call cond_wait() in the meantime. */
    synchronize_all_threads();

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
    }

    /* done */
    _finish_transaction();
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
    /* pull the right versions from other threads in order
       to reset our pages as part of an abort.

       Note that this function is also sometimes called from
       contention.c to clean up the state of a different thread,
       when we would really like it to be aborted now and it is
       suspended at a safe-point.

    */
    struct stm_priv_segment_info_s *pseg = get_priv_segment(segment_num);
    long remote_num = !segment_num;
    char *local_base = get_segment_base(segment_num);
    char *remote_base = get_segment_base(remote_num);

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

    /* throw away the content of the nursery */
    long bytes_in_nursery = throw_away_nursery(pseg);

    /* reset all the modified objects (incl. re-adding GCFLAG_WRITE_BARRIER) */
    reset_modified_from_other_segments(segment_num);

    /* reset the tl->shadowstack and thread_local_obj to their original
       value before the transaction start */
    stm_thread_local_t *tl = pseg->pub.running_thread;
    tl->shadowstack = pseg->shadowstack_at_start_of_transaction;
    tl->thread_local_obj = pseg->threadlocal_at_start_of_transaction;
    tl->last_abort__bytes_in_nursery = bytes_in_nursery;

    /* reset these lists to NULL too on abort */
    LIST_FREE(pseg->objects_pointing_to_nursery);
    LIST_FREE(pseg->large_overflow_objects);
}

static void abort_with_mutex(void)
{
    dprintf(("~~~ ABORT\n"));

    switch (STM_PSEGMENT->transaction_state) {
    case TS_REGULAR:
        break;
    case TS_INEVITABLE:
        stm_fatalerror("abort: transaction_state == TS_INEVITABLE");
    default:
        stm_fatalerror("abort: bad transaction_state == %d",
                       (int)STM_PSEGMENT->transaction_state);
    }
    assert(STM_PSEGMENT->running_pthread == pthread_self());

    abort_data_structures_from_segment_num(STM_SEGMENT->segment_num);

    stm_jmpbuf_t *jmpbuf_ptr = STM_SEGMENT->jmpbuf_ptr;

    /* clear memory registered on the thread-local */
    stm_thread_local_t *tl = STM_SEGMENT->running_thread;
    if (tl->mem_clear_on_abort)
        memset(tl->mem_clear_on_abort, 0, tl->mem_bytes_to_clear_on_abort);

    /* invoke the callbacks */
    invoke_and_clear_callbacks_on_abort();

    if (STM_SEGMENT->nursery_end == NSE_SIGABORT)
        STM_SEGMENT->nursery_end = NURSERY_END;   /* done aborting */

    _finish_transaction();
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

        wait_for_end_of_inevitable_transaction(true);
        STM_PSEGMENT->transaction_state = TS_INEVITABLE;
        STM_SEGMENT->jmpbuf_ptr = NULL;
        clear_callbacks_on_abort();
    }

    s_mutex_unlock();
}
