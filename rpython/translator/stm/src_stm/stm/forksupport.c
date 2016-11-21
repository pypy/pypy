/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif

static stm_thread_local_t *fork_this_tl;
static bool fork_was_in_transaction;


static void forksupport_prepare(void)
{
    if (stm_object_pages == NULL)
        return;

    /* So far we attempt to check this by walking all stm_thread_local_t,
       marking the one from the current thread, and verifying that it's not
       running a transaction.  This assumes that the stm_thread_local_t is just
       a __thread variable, so never changes threads.
    */
    s_mutex_lock();

    dprintf(("forksupport_prepare\n"));
    //fprintf(stderr, "[forking: for now, this operation can take some time]\n");

    stm_thread_local_t *this_tl = NULL;
    stm_thread_local_t *tl = stm_all_thread_locals;
    do {
        if (pthread_equal(*_get_cpth(tl), pthread_self())) {
            if (this_tl != NULL)
                stm_fatalerror("fork(): found several stm_thread_local_t"
                               " from the same thread");
            this_tl = tl;
        }
        tl = tl->next;
    } while (tl != stm_all_thread_locals);

    if (this_tl == NULL)
        stm_fatalerror("fork(): found no stm_thread_local_t from this thread");
    s_mutex_unlock();

    bool was_in_transaction = _stm_in_transaction(this_tl);
    if (!was_in_transaction)
        _stm_start_transaction(this_tl);
    assert(in_transaction(this_tl));

    stm_become_inevitable(this_tl, "fork");
    /* Note that the line above can still fail and abort, which should
       be fine */

    s_mutex_lock();
    synchronize_all_threads(STOP_OTHERS_UNTIL_MUTEX_UNLOCK);

    fork_this_tl = this_tl;
    fork_was_in_transaction = was_in_transaction;

    assert(_has_mutex());
    dprintf(("forksupport_prepare: from %p %p\n", fork_this_tl,
             fork_this_tl->creating_pthread[0]));
}

static void forksupport_parent(void)
{
    if (stm_object_pages == NULL)
        return;

    dprintf(("forksupport_parent: continuing to run %p %p\n", fork_this_tl,
             fork_this_tl->creating_pthread[0]));
    assert(_has_mutex());
    assert(_is_tl_registered(fork_this_tl));


    bool was_in_transaction = fork_was_in_transaction;
    s_mutex_unlock();

    if (!was_in_transaction) {
        _stm_commit_transaction();
    }

    dprintf(("forksupport_parent: continuing to run\n"));
}

static void fork_abort_thread(long i)
{
    struct stm_priv_segment_info_s *pr = get_priv_segment(i);
    stm_thread_local_t *tl = pr->pub.running_thread;
    dprintf(("forksupport_child: abort in seg%ld\n", i));
    assert(tl->last_associated_segment_num == i);
    assert(in_transaction(tl));
    assert(pr->transaction_state != TS_INEVITABLE);
    ensure_gs_register(i);
    assert(STM_SEGMENT->segment_num == i);

    s_mutex_lock();
    if (pr->transaction_state == TS_NONE) {
        /* just committed, TS_NONE but still has running_thread */

        /* do _finish_transaction() */
        STM_PSEGMENT->safe_point = SP_NO_TRANSACTION;
        list_clear(STM_PSEGMENT->objects_pointing_to_nursery);
        list_clear(STM_PSEGMENT->large_overflow_objects);

        s_mutex_unlock();
        return;
    }

#ifndef NDEBUG
    pr->running_pthread = pthread_self();
#endif
    tl->shadowstack = NULL;
    pr->shadowstack_at_start_of_transaction = NULL;
    stm_rewind_jmp_forget(tl);
    abort_with_mutex_no_longjmp();
    s_mutex_unlock();
}

static void forksupport_child(void)
{
    if (stm_object_pages == NULL)
        return;

    /* this new process contains no other thread, so we can
       just release these locks early */
    s_mutex_unlock();

    /* Re-init these locks; might be needed after a fork() */
    setup_modification_locks();


    /* Unregister all other stm_thread_local_t, mostly as a way to free
       the memory used by the shadowstacks
     */
    while (stm_all_thread_locals->next != stm_all_thread_locals) {
        if (stm_all_thread_locals == fork_this_tl)
            stm_unregister_thread_local(stm_all_thread_locals->next);
        else
            stm_unregister_thread_local(stm_all_thread_locals);
    }
    assert(stm_all_thread_locals == fork_this_tl);



    /* Force the interruption of other running segments (seg0 never runs)
     */
    long i;
    for (i = 1; i < NB_SEGMENTS; i++) {
        struct stm_priv_segment_info_s *pr = get_priv_segment(i);
        if (pr->pub.running_thread != NULL &&
            pr->pub.running_thread != fork_this_tl) {
            fork_abort_thread(i);
        }
    }

    /* Restore a few things: the new pthread_self(), and the %gs
       register */
    int segnum = fork_this_tl->last_associated_segment_num;
    assert(1 <= segnum && segnum < NB_SEGMENTS);
    *_get_cpth(fork_this_tl) = pthread_self();
    ensure_gs_register(segnum);
    assert(STM_SEGMENT->segment_num == segnum);

    if (!fork_was_in_transaction) {
        _stm_commit_transaction();
    }

    /* Done */
    dprintf(("forksupport_child: running one thread now\n"));
}


static void setup_forksupport(void)
{
    static bool fork_support_ready = false;

    if (!fork_support_ready) {
        int res = pthread_atfork(forksupport_prepare, forksupport_parent,
                                 forksupport_child);
        if (res != 0)
            stm_fatalerror("pthread_atfork() failed: %d", res);
        fork_support_ready = true;
    }
}
