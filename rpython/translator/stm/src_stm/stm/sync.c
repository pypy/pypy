/* Imported by rpython/translator/stm/import_stmgc.py */
#include <sys/syscall.h>
#include <sys/prctl.h>
#include <asm/prctl.h>
#include <time.h>
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif



static union {
    struct {
        pthread_mutex_t global_mutex;
        pthread_cond_t cond[_C_TOTAL];
        /* some additional pieces of global state follow */
        uint8_t in_use1[NB_SEGMENTS];   /* 1 if running a pthread, idx=0 unused */
    };
    char reserved[192];
} sync_ctl __attribute__((aligned(64)));


static void setup_sync(void)
{
    int err = pthread_mutex_init(&sync_ctl.global_mutex, NULL);
    if (err != 0)
        stm_fatalerror("mutex initialization: %d", err);

    long i;
    for (i = 0; i < _C_TOTAL; i++) {
        err = pthread_cond_init(&sync_ctl.cond[i], NULL);
        if (err != 0)
            stm_fatalerror("cond initialization: %d", err);
    }
}

static void teardown_sync(void)
{
    int err = pthread_mutex_destroy(&sync_ctl.global_mutex);
    if (err != 0)
        stm_fatalerror("mutex destroy: %d", err);

    long i;
    for (i = 0; i < _C_TOTAL; i++) {
        err = pthread_cond_destroy(&sync_ctl.cond[i]);
        if (err != 0)
            stm_fatalerror("cond destroy: %d", err);
    }

    memset(&sync_ctl, 0, sizeof(sync_ctl));
}

#ifndef NDEBUG
__thread bool _has_mutex_here;
static inline bool _has_mutex(void)
{
    return _has_mutex_here;
}
#endif

static void set_gs_register(char *value)
{
    if (UNLIKELY(syscall(SYS_arch_prctl, ARCH_SET_GS, (uint64_t)value) != 0))
        stm_fatalerror("syscall(arch_prctl, ARCH_SET_GS): %m");
}

static void ensure_gs_register(long segnum)
{
    if (STM_SEGMENT->segment_num != segnum) {
        set_gs_register(get_segment_base(segnum));
        assert(STM_SEGMENT->segment_num == segnum);
    }
}

static inline void s_mutex_lock(void)
{
    assert(!_has_mutex_here);
    int err = pthread_mutex_lock(&sync_ctl.global_mutex);
    if (UNLIKELY(err != 0))
        stm_fatalerror("pthread_mutex_lock: %d", err);
    assert((_has_mutex_here = true, 1));
}

static inline void s_mutex_unlock(void)
{
    assert(_has_mutex_here);
    int err = pthread_mutex_unlock(&sync_ctl.global_mutex);
    if (UNLIKELY(err != 0))
        stm_fatalerror("pthread_mutex_unlock: %d", err);
    assert((_has_mutex_here = false, 1));
}


static inline void cond_wait(enum cond_type_e ctype)
{
#ifdef STM_NO_COND_WAIT
    stm_fatalerror("*** cond_wait/%d called!", (int)ctype);
#endif

    assert(_has_mutex_here);
    int err = pthread_cond_wait(&sync_ctl.cond[ctype],
                                &sync_ctl.global_mutex);
    if (UNLIKELY(err != 0))
        stm_fatalerror("pthread_cond_wait/%d: %d", (int)ctype, err);
}

static inline void timespec_delay(struct timespec *t, double incr)
{
#ifdef CLOCK_REALTIME
    clock_gettime(CLOCK_REALTIME, t);
#else
    struct timeval tv;
    RPY_GETTIMEOFDAY(&tv);
    t->tv_sec = tv.tv_sec;
    t->tv_nsec = tv.tv_usec * 1000 + 999;
#endif

    long integral_part = (long)incr;
    t->tv_sec += integral_part;
    incr -= integral_part;
    assert(incr >= 0.0 && incr <= 1.0);

    long nsec = t->tv_nsec + (long)(incr * 1000000000.0);
    if (nsec >= 1000000000) {
        t->tv_sec += 1;
        nsec -= 1000000000;
        assert(nsec < 1000000000);
    }
    t->tv_nsec = nsec;
}

static bool cond_wait_timespec(enum cond_type_e ctype, struct timespec *pt)
{
#ifdef STM_NO_COND_WAIT
    stm_fatalerror("*** cond_wait/%d called!", (int)ctype);
#endif

 retry:
    assert(_has_mutex_here);

    int err = pthread_cond_timedwait(&sync_ctl.cond[ctype],
                                     &sync_ctl.global_mutex, pt);
    switch (err) {
    case 0:
        return true;     /* success */
    case ETIMEDOUT:
        return false;    /* timeout */
    case EINTR:
        goto retry;
    default:
        stm_fatalerror("pthread_cond_timedwait/%d: %d", (int)ctype, err);
    }
}

static bool cond_wait_timeout(enum cond_type_e ctype, double delay)
{
    struct timespec t;
    timespec_delay(&t, delay);
    return cond_wait_timespec(ctype, &t);
}

static inline void cond_signal(enum cond_type_e ctype)
{
    int err = pthread_cond_signal(&sync_ctl.cond[ctype]);
    if (UNLIKELY(err != 0))
        stm_fatalerror("pthread_cond_signal/%d: %d", (int)ctype, err);
}

static inline void cond_broadcast(enum cond_type_e ctype)
{
    int err = pthread_cond_broadcast(&sync_ctl.cond[ctype]);
    if (UNLIKELY(err != 0))
        stm_fatalerror("pthread_cond_broadcast/%d: %d", (int)ctype, err);
}

/************************************************************/


#if 0
void stm_wait_for_current_inevitable_transaction(void)
{
 restart:
    /* make sure there is no major collection happening, which
       could free some commit log entries */
    s_mutex_lock();

    struct stm_commit_log_entry_s *current = STM_PSEGMENT->last_commit_log_entry;

    /* XXX: don't do busy-waiting */
    while (current->next != NULL) {
        if (current->next == INEV_RUNNING) {
            s_mutex_unlock();
            usleep(10);
            /* some major collection could have freed "current", so
               restart from the beginning */
            goto restart;
        }
        current = current->next;
    }
    s_mutex_unlock();
}
#endif


static void acquire_thread_segment(stm_thread_local_t *tl)
{
    /* This function acquires a segment for the currently running thread,
       and set up the GS register if it changed. */
 retry_from_start:
    assert(_has_mutex());
    assert(_is_tl_registered(tl));

    int num = tl->last_associated_segment_num - 1; // 0..NB_SEG-2
    OPT_ASSERT(num >= 0);
    if (sync_ctl.in_use1[num+1] == 0) {
        /* fast-path: we can get the same segment number than the one
           we had before.  The value stored in GS may still be valid. */
        ensure_gs_register(num+1);
        dprintf(("acquired same segment: %d\n", num+1));
        goto got_num;
    }
    /* Look for the next free segment.  If there is none, wait for
       the condition variable. */
    int retries;
    for (retries = 0; retries < NB_SEGMENTS-1; retries++) {
        num = (num+1) % (NB_SEGMENTS-1);
        if (sync_ctl.in_use1[num+1] == 0) {
            /* we're getting 'num', a different number. */
            int old_num = tl->last_associated_segment_num;
            dprintf(("acquired different segment: %d->%d\n", old_num, num+1));
            tl->last_associated_segment_num = num+1;
            ensure_gs_register(num+1);
            dprintf(("                            %d->%d\n", old_num, num+1));
            (void)old_num;
            goto got_num;
        }
    }
    /* No segment available.  Wait until release_thread_segment()
       signals that one segment has been freed.  Note that we prefer
       waiting rather than detaching an inevitable transaction, here. */
    emit_wait(tl, STM_WAIT_FREE_SEGMENT);
    cond_wait(C_SEGMENT_FREE);

    goto retry_from_start;

 got_num:
    emit_wait_done(tl);
    OPT_ASSERT(num >= 0 && num < NB_SEGMENTS-1);
    sync_ctl.in_use1[num+1] = 1;
    assert(STM_SEGMENT->segment_num == num+1);
    assert(STM_SEGMENT->running_thread == NULL);
    assert(tl->last_associated_segment_num == STM_SEGMENT->segment_num);
    assert(!in_transaction(tl));
    STM_SEGMENT->running_thread = tl;
    assert(in_transaction(tl));
}

static void release_thread_segment(stm_thread_local_t *tl)
{
    int segnum;
    assert(_has_mutex());

    cond_signal(C_SEGMENT_FREE);
    cond_broadcast(C_SEGMENT_FREE_OR_SAFE_POINT_REQ);  /* often no listener */

    assert(STM_SEGMENT->running_thread == tl);
    segnum = STM_SEGMENT->segment_num;
    if (tl != NULL) {
        assert(tl->last_associated_segment_num == segnum);
        assert(in_transaction(tl));
        STM_SEGMENT->running_thread = NULL;
        assert(!in_transaction(tl));
    }

    assert(sync_ctl.in_use1[segnum] >= 1);
    sync_ctl.in_use1[segnum] = 0;
}

static void soon_finished_or_inevitable_thread_segment(void)
{
    int segnum = STM_SEGMENT->segment_num;
    assert(sync_ctl.in_use1[segnum] >= 1);
    sync_ctl.in_use1[segnum] = 2;   /* the value 2 is used to mark this case */
}

static bool any_soon_finished_or_inevitable_thread_segment(void)
{
    int num;
    for (num = 1; num < NB_SEGMENTS; num++)
        if (sync_ctl.in_use1[num] == 2)
            return true;
    return false;
}

__attribute__((unused))
static bool _seems_to_be_running_transaction(void)
{
    return (STM_SEGMENT->running_thread != NULL);
}

bool _stm_in_transaction(stm_thread_local_t *tl)
{
    int num = tl->last_associated_segment_num;
    OPT_ASSERT(1 <= num && num < NB_SEGMENTS);
    return in_transaction(tl);
}

void _stm_test_switch(stm_thread_local_t *tl)
{
    assert(_stm_in_transaction(tl));
    ensure_gs_register(tl->last_associated_segment_num);
    assert(STM_SEGMENT->running_thread == tl);
    exec_local_finalizers();
}

void _stm_test_switch_segment(int segnum)
{
    ensure_gs_register(segnum+1);
}

#if STM_TESTS
void _stm_start_safe_point(void)
{
    assert(STM_PSEGMENT->safe_point == SP_RUNNING);
    STM_PSEGMENT->safe_point = SP_WAIT_FOR_OTHER_THREAD;
}

void _stm_stop_safe_point(void)
{
    assert(STM_PSEGMENT->safe_point == SP_WAIT_FOR_OTHER_THREAD);
    STM_PSEGMENT->safe_point = SP_RUNNING;

    stm_safe_point();
}
#endif



/************************************************************/


#ifndef NDEBUG
static bool _safe_points_requested = false;
#endif

static void signal_everybody_to_pause_running(void)
{
    assert(_safe_points_requested == false);
    assert((_safe_points_requested = true, 1));
    assert(_has_mutex());

    long i;
    for (i = 1; i < NB_SEGMENTS; i++) {
        if (get_segment(i)->nursery_end == NURSERY_END)
            get_segment(i)->nursery_end = NSE_SIGPAUSE;
    }
    assert(!pause_signalled);
    pause_signalled = true;
    dprintf(("request to pause\n"));
    cond_broadcast(C_SEGMENT_FREE_OR_SAFE_POINT_REQ);
}

static inline long count_other_threads_sp_running(void)
{
    /* Return the number of other threads in SP_RUNNING.
       Asserts that SP_RUNNING threads still have the NSE_SIGxxx.
       (A detached inevitable transaction is still SP_RUNNING.) */
    long i;
    long result = 0;
    int my_num;

    my_num = STM_SEGMENT->segment_num;
    for (i = 1; i < NB_SEGMENTS; i++) {
        if (i != my_num && get_priv_segment(i)->safe_point == SP_RUNNING) {
            assert(get_segment(i)->nursery_end <= _STM_NSE_SIGNAL_MAX);
            result++;
        }
    }
    return result;
}

static void remove_requests_for_safe_point(void)
{
    assert(pause_signalled);
    pause_signalled = false;
    assert(_safe_points_requested == true);
    assert((_safe_points_requested = false, 1));

    long i;
    for (i = 1; i < NB_SEGMENTS; i++) {
        assert(get_segment(i)->nursery_end != NURSERY_END);
        if (get_segment(i)->nursery_end == NSE_SIGPAUSE)
            get_segment(i)->nursery_end = NURSERY_END;
    }
    dprintf(("request removed\n"));
    cond_broadcast(C_REQUEST_REMOVED);
}

static void enter_safe_point_if_requested(void)
{
    if (STM_SEGMENT->nursery_end == NURSERY_END)
        return;    /* fast path: no safe point requested */

    assert(_seems_to_be_running_transaction());
    assert(_has_mutex());
    while (1) {
        if (must_abort())
            abort_with_mutex();

        if (STM_SEGMENT->nursery_end == NURSERY_END)
            break;    /* no safe point requested */

        dprintf(("enter safe point\n"));
        assert(!STM_SEGMENT->no_safe_point_here);
        assert(STM_SEGMENT->nursery_end == NSE_SIGPAUSE);
        assert(pause_signalled);

        /* If we are requested to enter a safe-point, we cannot proceed now.
           Wait until the safe-point request is removed for us. */
#ifdef STM_TESTS
        abort_with_mutex();
#endif
        EMIT_WAIT(STM_WAIT_SYNC_PAUSE);
        cond_signal(C_AT_SAFE_POINT);
        STM_PSEGMENT->safe_point = SP_WAIT_FOR_C_REQUEST_REMOVED;
        cond_wait(C_REQUEST_REMOVED);
        STM_PSEGMENT->safe_point = SP_RUNNING;
        assert(!STM_SEGMENT->no_safe_point_here);
        dprintf(("left safe point\n"));
    }
    EMIT_WAIT_DONE();
}

static void synchronize_all_threads(enum sync_type_e sync_type)
{
 restart:
    assert(_has_mutex());
    enter_safe_point_if_requested();

    /* Only one thread should reach this point concurrently.  This is
       why: if several threads call this function, the first one that
       goes past this point will set the "request safe point" on all
       other threads; then none of the other threads will go past the
       enter_safe_point_if_requested() above.
    */
    if (UNLIKELY(globally_unique_transaction)) {
        assert(count_other_threads_sp_running() == 0);
        return;
    }

    signal_everybody_to_pause_running();

    /* If some other threads are SP_RUNNING, we cannot proceed now.
       Wait until all other threads are suspended. */
    while (count_other_threads_sp_running() > 0) {

        intptr_t detached = fetch_detached_transaction();
        if (detached != 0) {
            EMIT_WAIT_DONE();
            remove_requests_for_safe_point();    /* => C_REQUEST_REMOVED */
            s_mutex_unlock();
            commit_fetched_detached_transaction(detached);
            s_mutex_lock();
            goto restart;
        }
        EMIT_WAIT(STM_WAIT_SYNCING);
        STM_PSEGMENT->safe_point = SP_WAIT_FOR_C_AT_SAFE_POINT;
        cond_wait_timeout(C_AT_SAFE_POINT, 0.00001);
        /* every 10 microsec, try again fetch_detached_transaction() */
        STM_PSEGMENT->safe_point = SP_RUNNING;

        if (must_abort()) {
            remove_requests_for_safe_point();    /* => C_REQUEST_REMOVED */
            abort_with_mutex();
        }
    }
    EMIT_WAIT_DONE();

    if (UNLIKELY(sync_type == STOP_OTHERS_AND_BECOME_GLOBALLY_UNIQUE)) {
        globally_unique_transaction = true;
        assert(STM_SEGMENT->nursery_end == NSE_SIGPAUSE);
        STM_SEGMENT->nursery_end = NURSERY_END;
        return;  /* don't remove the requests for safe-points in this case */
    }

    /* Remove the requests for safe-points now.  In principle we should
       remove it later, when the caller is done, but this is equivalent
       as long as we hold the mutex.
    */
    remove_requests_for_safe_point();    /* => C_REQUEST_REMOVED */
}

static void committed_globally_unique_transaction(void)
{
    assert(globally_unique_transaction);
    assert(STM_SEGMENT->nursery_end == NURSERY_END);
    STM_SEGMENT->nursery_end = NSE_SIGPAUSE;
    globally_unique_transaction = false;
    remove_requests_for_safe_point();
}

void _stm_collectable_safe_point(void)
{
    /* If 'nursery_end' was set to NSE_SIGxxx by another thread,
       we end up here as soon as we try to call stm_allocate() or do
       a call to stm_safe_point().
    */
    s_mutex_lock();
    enter_safe_point_if_requested();
    s_mutex_unlock();
}
