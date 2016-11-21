/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif
#include <errno.h>


/* Idea: if stm_leave_transactional_zone() is quickly followed by
   stm_enter_transactional_zone() in the same thread, then we should
   simply try to have one inevitable transaction that does both sides.
   This is useful if there are many such small interruptions.

   stm_leave_transactional_zone() tries to make sure the transaction
   is inevitable, and then sticks the current 'stm_thread_local_t *'
   into _stm_detached_inevitable_from_thread.
   stm_enter_transactional_zone() has a fast-path if the same
   'stm_thread_local_t *' is still there.

   If a different thread grabs it, it atomically replaces the value in
   _stm_detached_inevitable_from_thread with -1, commits it (this part
   involves reading for example the shadowstack of the thread that
   originally detached), and at the point where we know the original
   stm_thread_local_t is no longer relevant, we reset
   _stm_detached_inevitable_from_thread to 0.

   The value that stm_leave_transactional_zone() sticks inside
   _stm_detached_inevitable_from_thread is actually
   'tl->self_or_0_if_atomic'.  This value is 0 if and only if 'tl' is
   current running a transaction *and* this transaction is atomic.  So
   if we're running an atomic transaction, then
   _stm_detached_inevitable_from_thread remains 0 across
   leave/enter_transactional.
*/

volatile intptr_t _stm_detached_inevitable_from_thread;


static void setup_detach(void)
{
    _stm_detached_inevitable_from_thread = 0;
}


void _stm_leave_noninevitable_transactional_zone(void)
{
    int saved_errno = errno;

    if (STM_PSEGMENT->atomic_nesting_levels == 0) {
        dprintf(("leave_noninevitable_transactional_zone\n"));
        _stm_become_inevitable(MSG_INEV_DONT_SLEEP);

        /* did it work? */
        if (STM_PSEGMENT->transaction_state == TS_INEVITABLE) {   /* yes */
            dprintf((
                "leave_noninevitable_transactional_zone: now inevitable\n"));
            stm_thread_local_t *tl = STM_SEGMENT->running_thread;
            _stm_detach_inevitable_transaction(tl);
        }
        else {   /* no */
            dprintf(("leave_noninevitable_transactional_zone: commit\n"));
            _stm_commit_transaction();
        }
    }
    else {
        /* we're atomic, so we can't commit at all */
        dprintf(("leave_noninevitable_transactional_zone atomic\n"));
        _stm_become_inevitable("leave_noninevitable_transactional_zone atomic");
        assert(STM_PSEGMENT->transaction_state == TS_INEVITABLE);
        assert(_stm_detached_inevitable_from_thread == 0);
        assert(STM_SEGMENT->running_thread->self_or_0_if_atomic == 0);
        /* no point in calling _stm_detach_inevitable_transaction()
           because it would store 0 into a place that is already 0, as
           checked by the asserts above */
    }

    errno = saved_errno;
}

static void commit_external_inevitable_transaction(void)
{
    assert(STM_PSEGMENT->transaction_state == TS_INEVITABLE); /* can't abort */
    _core_commit_transaction(/*external=*/ true);
}

void _stm_reattach_transaction(intptr_t self)
{
    intptr_t old;
    int saved_errno = errno;
    stm_thread_local_t *tl = (stm_thread_local_t *)self;

    /* if 'self_or_0_if_atomic == 0', it means that we are trying to
       reattach in a thread that is currently running a transaction
       that is atomic.  That should only be possible if we're
       inevitable too.  And in that case,
       '_stm_detached_inevitable_from_thread' must always be 0, and
       the previous call to compare_and_swap(0, 0) should have worked
       (and done nothing), so we should not end here.
    */
    if (self == 0)
        stm_fatalerror("atomic inconsistency");

 restart:
    old = _stm_detached_inevitable_from_thread;
    if (old != 0) {
        if (old == -1) {
            /* busy-loop: wait until _stm_detached_inevitable_from_thread
               is reset to a value different from -1 */
            dprintf(("reattach_transaction: busy wait...\n"));
            while (_stm_detached_inevitable_from_thread == -1)
                stm_spin_loop();

            /* then retry */
            goto restart;
        }

        if (!__sync_bool_compare_and_swap(&_stm_detached_inevitable_from_thread,
                                          old, -1))
            goto restart;

        stm_thread_local_t *old_tl = (stm_thread_local_t *)old;
        int remote_seg_num = old_tl->last_associated_segment_num;
        dprintf(("reattach_transaction: commit detached from seg %d\n",
                 remote_seg_num));

        assert(tl != old_tl);

        // XXX: not sure if the next line is a good idea
        tl->last_associated_segment_num = remote_seg_num;
        ensure_gs_register(remote_seg_num);
        assert(old_tl == STM_SEGMENT->running_thread);
        timing_event(STM_SEGMENT->running_thread, STM_TRANSACTION_REATTACH);
        commit_external_inevitable_transaction();
    }
    dprintf(("reattach_transaction: start a new transaction\n"));
    _stm_start_transaction(tl);
    errno = saved_errno;
}

void stm_force_transaction_break(stm_thread_local_t *tl)
{
    dprintf(("> stm_force_transaction_break()\n"));
    assert(STM_SEGMENT->running_thread == tl);
    assert(!stm_is_atomic(tl));
    _stm_commit_transaction();
    _stm_start_transaction(tl);
}

static intptr_t fetch_detached_transaction(void)
{
    intptr_t cur;
 restart:
    cur = _stm_detached_inevitable_from_thread;
    if (cur == 0) {    /* fast-path */
        return 0;   /* _stm_detached_inevitable_from_thread not changed */
    }
    if (cur == -1) {
        /* busy-loop: wait until _stm_detached_inevitable_from_thread
           is reset to a value different from -1 */
        while (_stm_detached_inevitable_from_thread == -1)
            stm_spin_loop();
        goto restart;
    }
    if (!__sync_bool_compare_and_swap(&_stm_detached_inevitable_from_thread,
                                      cur, -1))
        goto restart;

    /* this is the only case where we grabbed a detached transaction.
       _stm_detached_inevitable_from_thread is still -1, until
       commit_fetched_detached_transaction() is called. */
    assert(_stm_detached_inevitable_from_thread == -1);
    return cur;
}

static void commit_fetched_detached_transaction(intptr_t old)
{
    /* Here, 'seg_num' is the segment that contains the detached
       inevitable transaction from fetch_detached_transaction(),
       probably belonging to an unrelated thread.  We fetched it,
       which means that nobody else can concurrently fetch it now, but
       everybody will see that there is still a concurrent inevitable
       transaction.  This should guarantee there are no race
       conditions.
    */
    int mysegnum = STM_SEGMENT->segment_num;
    int segnum = ((stm_thread_local_t *)old)->last_associated_segment_num;
    dprintf(("commit_fetched_detached_transaction from seg %d\n", segnum));
    assert(segnum > 0);

    ensure_gs_register(segnum);
    assert(((stm_thread_local_t *)old) == STM_SEGMENT->running_thread);
    timing_event(STM_SEGMENT->running_thread, STM_TRANSACTION_REATTACH);
    commit_external_inevitable_transaction();
    ensure_gs_register(mysegnum);
}

static void commit_detached_transaction_if_from(stm_thread_local_t *tl)
{
    intptr_t old;
 restart:
    old = _stm_detached_inevitable_from_thread;
    if (old == (intptr_t)tl) {
        if (!__sync_bool_compare_and_swap(&_stm_detached_inevitable_from_thread,
                                          old, -1))
            goto restart;
        commit_fetched_detached_transaction(old);
        return;
    }
    if (old == -1) {
        /* busy-loop: wait until _stm_detached_inevitable_from_thread
           is reset to a value different from -1 */
        while (_stm_detached_inevitable_from_thread == -1)
            stm_spin_loop();
        goto restart;
    }
}

uintptr_t stm_is_atomic(stm_thread_local_t *tl)
{
    assert(STM_SEGMENT->running_thread == tl);
    if (tl->self_or_0_if_atomic != 0) {
        assert(tl->self_or_0_if_atomic == (intptr_t)tl);
        assert(STM_PSEGMENT->atomic_nesting_levels == 0);
    }
    else {
        assert(STM_PSEGMENT->atomic_nesting_levels > 0);
    }
    return STM_PSEGMENT->atomic_nesting_levels;
}

#define HUGE_INTPTR_VALUE  0x3000000000000000L

void stm_enable_atomic(stm_thread_local_t *tl)
{
    if (!stm_is_atomic(tl)) {
        tl->self_or_0_if_atomic = 0;
        /* increment 'nursery_mark' by HUGE_INTPTR_VALUE, so that
           stm_should_break_transaction() returns always false */
        intptr_t mark = (intptr_t)STM_SEGMENT->nursery_mark;
        if (mark < 0)
            mark = 0;
        if (mark >= HUGE_INTPTR_VALUE)
            mark = HUGE_INTPTR_VALUE - 1;
        mark += HUGE_INTPTR_VALUE;
        STM_SEGMENT->nursery_mark = (stm_char *)mark;
    }
    STM_PSEGMENT->atomic_nesting_levels++;
}

void stm_disable_atomic(stm_thread_local_t *tl)
{
    if (!stm_is_atomic(tl))
        stm_fatalerror("stm_disable_atomic(): already not atomic");

    STM_PSEGMENT->atomic_nesting_levels--;

    if (STM_PSEGMENT->atomic_nesting_levels == 0) {
        tl->self_or_0_if_atomic = (intptr_t)tl;
        /* decrement 'nursery_mark' by HUGE_INTPTR_VALUE, to cancel
           what was done in stm_enable_atomic() */
        intptr_t mark = (intptr_t)STM_SEGMENT->nursery_mark;
        mark -= HUGE_INTPTR_VALUE;
        if (mark < 0)
            mark = 0;
        STM_SEGMENT->nursery_mark = (stm_char *)mark;
    }
}
