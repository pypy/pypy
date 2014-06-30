/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


enum contention_kind_e {

    /* A write-write contention occurs when we running our transaction
       and detect that we are about to write to an object that another
       thread is also writing to.  This kind of contention must be
       resolved before continuing.  This *must* abort one of the two
       threads: the caller's thread is not at a safe-point, so cannot
       wait! */
    WRITE_WRITE_CONTENTION,

    /* A write-read contention occurs when we are trying to commit: it
       means that an object we wrote to was also read by another
       transaction.  Even though it would seem obvious that we should
       just abort the other thread and proceed in our commit, a more
       subtle answer would be in some cases to wait for the other thread
       to commit first.  It would commit having read the old value, and
       then we can commit our change to it. */
    WRITE_READ_CONTENTION,

    /* An inevitable contention occurs when we're trying to become
       inevitable but another thread already is.  We can never abort the
       other thread in this case, but we still have the choice to abort
       ourselves or pause until the other thread commits. */
    INEVITABLE_CONTENTION,
};

struct contmgr_s {
    enum contention_kind_e kind;
    struct stm_priv_segment_info_s *other_pseg;
    bool abort_other;
    bool try_sleep;  // XXX add a way to timeout, but should handle repeated
                     // calls to contention_management() to avoid re-sleeping
                     // for the whole duration
};


/************************************************************/


__attribute__((unused))
static void cm_always_abort_myself(struct contmgr_s *cm)
{
    cm->abort_other = false;
}

__attribute__((unused))
static void cm_always_abort_other(struct contmgr_s *cm)
{
    cm->abort_other = true;
}

__attribute__((unused))
static void cm_abort_the_younger(struct contmgr_s *cm)
{
    if (STM_PSEGMENT->start_time >= cm->other_pseg->start_time) {
        /* We started after the other thread.  Abort */
        cm->abort_other = false;
    }
    else {
        cm->abort_other = true;
    }
}

__attribute__((unused))
static void cm_always_wait_for_other_thread(struct contmgr_s *cm)
{
    /* we tried this contention management, but it seems to have
       very bad cases: if thread 1 always reads an object in every
       transaction, and thread 2 wants to write this object just
       once, then thread 2 will pause when it tries to commit;
       it will wait until thread 1 committed; but by the time
       thread 2 resumes again, thread 1 has already started the
       next transaction and read the object again.
    */
    cm_abort_the_younger(cm);
    cm->try_sleep = true;
}

__attribute__((unused))
static void cm_pause_if_younger(struct contmgr_s *cm)
{
    if (STM_PSEGMENT->start_time >= cm->other_pseg->start_time) {
        /* We started after the other thread.  Pause */
        cm->try_sleep = true;
        cm->abort_other = false;
    }
    else {
        cm->abort_other = true;
    }
}


/************************************************************/


static bool contention_management(uint8_t other_segment_num,
                                  enum contention_kind_e kind,
                                  object_t *obj)
{
    assert(_has_mutex());
    assert(other_segment_num != STM_SEGMENT->segment_num);

    bool others_may_have_run = false;
    if (must_abort())
        abort_with_mutex();

    /* Who should abort here: this thread, or the other thread? */
    struct contmgr_s contmgr;
    contmgr.kind = kind;
    contmgr.other_pseg = get_priv_segment(other_segment_num);
    contmgr.abort_other = false;
    contmgr.try_sleep = false;

    /* Pick one contention management... could be made dynamically choosable */
#ifdef STM_TESTS
    cm_abort_the_younger(&contmgr);
#else
    cm_pause_if_younger(&contmgr);
#endif

    /* Fix the choices that are found incorrect due to TS_INEVITABLE
       or is_abort() */
    if (is_abort(contmgr.other_pseg->pub.nursery_end)) {
        contmgr.abort_other = true;
        contmgr.try_sleep = false;
    }
    else if (STM_PSEGMENT->transaction_state == TS_INEVITABLE) {
        assert(contmgr.other_pseg->transaction_state != TS_INEVITABLE);
        contmgr.abort_other = true;
        contmgr.try_sleep = false;
    }
    else if (contmgr.other_pseg->transaction_state == TS_INEVITABLE) {
        contmgr.abort_other = false;
    }


    int wait_category =
        kind == WRITE_READ_CONTENTION ? STM_TIME_WAIT_WRITE_READ :
        kind == INEVITABLE_CONTENTION ? STM_TIME_WAIT_INEVITABLE :
        STM_TIME_WAIT_OTHER;

    int abort_category =
        kind == WRITE_WRITE_CONTENTION ? STM_TIME_RUN_ABORTED_WRITE_WRITE :
        kind == WRITE_READ_CONTENTION ? STM_TIME_RUN_ABORTED_WRITE_READ :
        kind == INEVITABLE_CONTENTION ? STM_TIME_RUN_ABORTED_INEVITABLE :
        STM_TIME_RUN_ABORTED_OTHER;


    if (contmgr.try_sleep && kind != WRITE_WRITE_CONTENTION &&
        contmgr.other_pseg->safe_point != SP_WAIT_FOR_C_TRANSACTION_DONE) {
        others_may_have_run = true;
        /* Sleep.

           - Not for write-write contentions, because we're not at a
             safe-point.

           - To prevent loops of threads waiting for each others, use
             a crude heuristic of never pausing for a thread that is
             itself already paused here.
        */
        contmgr.other_pseg->signal_when_done = true;
        marker_contention(kind, false, other_segment_num, obj);

        change_timing_state(wait_category);

        /* tell the other to commit ASAP */
        signal_other_to_commit_soon(contmgr.other_pseg);

        dprintf(("pausing...\n"));
        cond_signal(C_AT_SAFE_POINT);
        STM_PSEGMENT->safe_point = SP_WAIT_FOR_C_TRANSACTION_DONE;
        cond_wait(C_TRANSACTION_DONE);
        STM_PSEGMENT->safe_point = SP_RUNNING;
        dprintf(("pausing done\n"));

        if (must_abort())
            abort_with_mutex();

        struct stm_priv_segment_info_s *pseg =
            get_priv_segment(STM_SEGMENT->segment_num);
        double elapsed =
            change_timing_state_tl(pseg->pub.running_thread,
                                   STM_TIME_RUN_CURRENT);
        marker_copy(pseg->pub.running_thread, pseg,
                    wait_category, elapsed);
    }

    else if (!contmgr.abort_other) {
        /* tell the other to commit ASAP, since it causes aborts */
        signal_other_to_commit_soon(contmgr.other_pseg);

        dprintf(("abort in contention: kind %d\n", kind));
        STM_SEGMENT->nursery_end = abort_category;
        marker_contention(kind, false, other_segment_num, obj);
        abort_with_mutex();
    }

    else {
        /* We have to signal the other thread to abort, and wait until
           it does. */
        contmgr.other_pseg->pub.nursery_end = abort_category;
        marker_contention(kind, true, other_segment_num, obj);

        int sp = contmgr.other_pseg->safe_point;
        switch (sp) {

        case SP_RUNNING:
            /* The other thread is running now, so as NSE_SIGABORT was
               set in its 'nursery_end', it will soon enter a
               mutex_lock() and thus abort.

               In this case, we will wait until it broadcasts "I'm done
               aborting".  Important: this is not a safe point of any
               kind!  The shadowstack may not be correct here.  It
               should not end in a deadlock, because the target thread
               is, in principle, guaranteed to call abort_with_mutex()
               very soon.  Just to be on the safe side, make it really
               impossible for the target thread to later enter the same
               cond_wait(C_ABORTED) (and thus wait, possibly for us,
               ending in a deadlock): check again must_abort() first.
            */
            if (must_abort())
                abort_with_mutex();

            others_may_have_run = true;
            dprintf(("contention: wait C_ABORTED...\n"));
            cond_wait(C_ABORTED);
            dprintf(("contention: done\n"));

            if (must_abort())
                abort_with_mutex();
            break;

        /* The other cases are where the other thread is at a
           safe-point.  We wake it up by sending the correct signal.
           We don't have to wait here: the other thread will not do
           anything more than abort when it really wakes up later.
        */
        case SP_WAIT_FOR_C_REQUEST_REMOVED:
            cond_broadcast(C_REQUEST_REMOVED);
            break;

        case SP_WAIT_FOR_C_AT_SAFE_POINT:
            cond_broadcast(C_AT_SAFE_POINT);
            break;

        case SP_WAIT_FOR_C_TRANSACTION_DONE:
            cond_broadcast(C_TRANSACTION_DONE);
            break;

#ifdef STM_TESTS
        case SP_WAIT_FOR_OTHER_THREAD:
            /* for tests: the other thread will abort as soon as
               stm_stop_safe_point() is called */
            break;
#endif

        default:
            stm_fatalerror("unexpected other_pseg->safe_point: %d", sp);
        }

        if (is_aborting_now(other_segment_num)) {
            /* The other thread is blocked in a safe-point with NSE_SIGABORT.
               We don't have to wake it up right now, but we know it will
               abort as soon as it wakes up.  We can safely force it to
               reset its state now. */
            dprintf(("killing data structures\n"));
            abort_data_structures_from_segment_num(other_segment_num);
        }
        dprintf(("killed other thread\n"));

        /* we should commit soon, we caused an abort */
        //signal_other_to_commit_soon(get_priv_segment(STM_SEGMENT->segment_num));
        if (!STM_PSEGMENT->signalled_to_commit_soon) {
            STM_PSEGMENT->signalled_to_commit_soon = true;
            stmcb_commit_soon();
        }
    }
    return others_may_have_run;
}

static void write_write_contention_management(uintptr_t lock_idx,
                                              object_t *obj)
{
    s_mutex_lock();

    uint8_t prev_owner = ((volatile uint8_t *)write_locks)[lock_idx];
    if (prev_owner != 0 && prev_owner != STM_PSEGMENT->write_lock_num) {

        uint8_t other_segment_num = prev_owner;
        assert(get_priv_segment(other_segment_num)->write_lock_num ==
               prev_owner);

        contention_management(other_segment_num, WRITE_WRITE_CONTENTION, obj);

        /* now we return into _stm_write_slowpath() and will try again
           to acquire the write lock on our object. */
    }

    s_mutex_unlock();
}

static bool write_read_contention_management(uint8_t other_segment_num,
                                             object_t *obj)
{
    return contention_management(other_segment_num, WRITE_READ_CONTENTION, obj);
}

static void inevitable_contention_management(uint8_t other_segment_num)
{
    contention_management(other_segment_num, INEVITABLE_CONTENTION, NULL);
}
