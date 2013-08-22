/* Imported by rpython/translator/stm/import_stmgc.py */
#include "stmimpl.h"


#define LENGTH_SHADOW_STACK   163840


__thread gcptr *stm_shadowstack;
static unsigned long stm_regular_length_limit = 10000;
static revision_t sync_required = 0;

void stm_set_transaction_length(long length_max)
{
    BecomeInevitable("set_transaction_length");
    if (length_max <= 0) {
        length_max = 1;
    }
    stm_regular_length_limit = length_max;
}

_Bool stm_should_break_transaction(void)
{
    struct tx_descriptor *d = thread_descriptor;

    /* a single comparison to handle all cases:

     - first, if sync_required == -1, this should return True.

     - if d->atomic, then we should return False.  This is done by
       forcing reads_size_limit to ULONG_MAX as soon as atomic > 0.

     - otherwise, if is_inevitable(), then we should return True.
       This is done by forcing both reads_size_limit and
       reads_size_limit_nonatomic to 0 in that case.

     - finally, the default case: return True if d->count_reads is
       greater than reads_size_limit == reads_size_limit_nonatomic.
    */
#ifdef _GC_DEBUG
    /* reads_size_limit is ULONG_MAX if d->atomic, or else it is equal to
       reads_size_limit_nonatomic. */
    assert(d->reads_size_limit == (d->atomic ? ULONG_MAX :
                                   d->reads_size_limit_nonatomic));
    /* if is_inevitable(), reads_size_limit_nonatomic should be 0
       (and thus reads_size_limit too, if !d->atomic.) */
    if (d->active == 2)
        assert(d->reads_size_limit_nonatomic == 0);
#endif

    return (sync_required | d->count_reads) >= d->reads_size_limit;
}

static void init_shadowstack(void)
{
    struct tx_descriptor *d = thread_descriptor;
    d->shadowstack = stm_malloc(sizeof(gcptr) * LENGTH_SHADOW_STACK);
    if (!d->shadowstack) {
        stm_fatalerror("out of memory: shadowstack\n");
    }
    stm_shadowstack = d->shadowstack;
    d->shadowstack_end_ref = &stm_shadowstack;
    stm_push_root(END_MARKER_ON);
}

static void done_shadowstack(void)
{
    struct tx_descriptor *d = thread_descriptor;
    gcptr x = stm_pop_root();
    assert(x == END_MARKER_ON);
    assert(stm_shadowstack == d->shadowstack);
    stm_shadowstack = NULL;
    stm_free(d->shadowstack, sizeof(gcptr) * LENGTH_SHADOW_STACK);
}

void stm_set_max_aborts(int max_aborts)
{
    struct tx_descriptor *d = thread_descriptor;
    d->max_aborts = max_aborts;
}

int stm_enter_callback_call(void)
{
    int token = (thread_descriptor == NULL);
    dprintf(("enter_callback_call(tok=%d)\n", token));
    if (token == 1) {
        stmgcpage_acquire_global_lock();
#ifdef STM_BARRIER_COUNT
        static int seen = 0;
        if (!seen) {
            seen = 1;
            atexit(&stm_print_barrier_count);
        }
#endif
        DescriptorInit();
        stmgc_init_nursery();
        init_shadowstack();
        stmgcpage_release_global_lock();
    }
    BeginInevitableTransaction();
    return token;
}

void stm_leave_callback_call(int token)
{
    dprintf(("leave_callback_call(%d)\n", token));
    if (token == 1)
        stmgc_minor_collect();   /* force everything out of the nursery */

    CommitTransaction();

    if (token == 1) {
        stmgcpage_acquire_global_lock();
        done_shadowstack();
        stmgc_done_nursery();
        DescriptorDone();
        stmgcpage_release_global_lock();
    }
}

void stm_initialize(void)
{
    int r = stm_enter_callback_call();
    if (r != 1)
        stm_fatalerror("stm_initialize: already initialized\n");
}

void stm_finalize(void)
{
    stm_leave_callback_call(1);
}

/************************************************************/

void stm_perform_transaction(gcptr arg, int (*callback)(gcptr, int))
{   /* must save roots around this call */
    jmp_buf _jmpbuf;
    long volatile v_counter = 0;
    gcptr *volatile v_saved_value = stm_shadowstack;
    long volatile v_atomic;

    stm_push_root(arg);
    stm_push_root(END_MARKER_OFF);

    if (!(v_atomic = thread_descriptor->atomic))
        CommitTransaction();

#ifdef _GC_ON_CPYTHON
    volatile PyThreadState *v_ts = PyGILState_GetThisThreadState();
    volatile int v_recursion_depth = v_ts->recursion_depth;
#endif

    setjmp(_jmpbuf);

#ifdef _GC_ON_CPYTHON
    v_ts->recursion_depth = v_recursion_depth;
#endif

    /* After setjmp(), the local variables v_* are preserved because they
     * are volatile.  The other variables are only declared here. */
    struct tx_descriptor *d = thread_descriptor;
    long counter, result;
    counter = v_counter;
    d->atomic = v_atomic;
    stm_shadowstack = v_saved_value + 2;   /*skip the two values pushed above*/

    do {
        v_counter = counter + 1;
        /* If counter==0, initialize 'reads_size_limit_nonatomic' from the
           configured length limit.  If counter>0, we did an abort, which
           has configured 'reads_size_limit_nonatomic' to a smaller value.
           When such a shortened transaction succeeds, the next one will
           see its length limit doubled, up to the maximum. */
        if (counter == 0) {
            unsigned long limit = d->reads_size_limit_nonatomic;
            if (limit != 0 && limit < (stm_regular_length_limit >> 1))
                limit = (limit << 1) | 1;
            else
                limit = stm_regular_length_limit;
            d->reads_size_limit_nonatomic = limit;
        }
        if (!d->atomic) {
            BeginTransaction(&_jmpbuf);
        }
        else {
            /* atomic transaction: a common case is that callback() returned
               even though we are atomic because we need a major GC.  For
               that case, release and reaquire the rw lock here. */
            stm_possible_safe_point();
        }

        /* invoke the callback in the new transaction */
        arg = v_saved_value[0];
        result = callback(arg, counter);
        assert(stm_shadowstack == v_saved_value + 2);

        v_atomic = d->atomic;
        if (!d->atomic)
            CommitTransaction();

        counter = 0;
    }
    while (result > 0);  /* continue as long as callback() returned > 0 */

    if (d->atomic) {
        if (d->setjmp_buf == &_jmpbuf) {
            BecomeInevitable("perform_transaction left with atomic");
        }
    }
    else {
        BeginInevitableTransaction();
    }

    gcptr x = stm_pop_root();   /* pop the END_MARKER */
    assert(x == END_MARKER_OFF || x == END_MARKER_ON);
    stm_pop_root();             /* pop the 'arg' */
    assert(stm_shadowstack == v_saved_value);
}

void stm_commit_transaction(void)
{   /* must save roots around this call */
    struct tx_descriptor *d = thread_descriptor;
    if (!d->atomic)
        CommitTransaction();
}

void stm_begin_inevitable_transaction(void)
{   /* must save roots around this call */
    struct tx_descriptor *d = thread_descriptor;
    if (!d->atomic)
        BeginInevitableTransaction();
}

void stm_become_inevitable(const char *reason)
{
    BecomeInevitable(reason);
}

int stm_in_transaction(void)
{
    struct tx_descriptor *d = thread_descriptor;
    return d && d->active;
}

/************************************************************/

/* a multi-reader, single-writer lock: transactions normally take a reader
   lock, so don't conflict with each other; when we need to do a global GC,
   we take a writer lock to "stop the world".  Note the initializer here,
   which should give the correct priority for stm_possible_safe_point(). */
static pthread_rwlock_t rwlock_shared =
    PTHREAD_RWLOCK_WRITER_NONRECURSIVE_INITIALIZER_NP;

static struct tx_descriptor *in_single_thread = NULL;  /* for debugging */

void stm_start_sharedlock(void)
{
    int err = pthread_rwlock_rdlock(&rwlock_shared);
    if (err != 0)
        stm_fatalerror("stm_start_sharedlock: "
                       "pthread_rwlock_rdlock failure\n");
    //assert(stmgc_nursery_hiding(thread_descriptor, 0));
    dprintf(("stm_start_sharedlock\n"));
}

void stm_stop_sharedlock(void)
{
    dprintf(("stm_stop_sharedlock\n"));
    //assert(stmgc_nursery_hiding(thread_descriptor, 1));
    int err = pthread_rwlock_unlock(&rwlock_shared);
    if (err != 0)
        stm_fatalerror("stm_stop_sharedlock: "
                       "pthread_rwlock_unlock failure\n");
}

static void start_exclusivelock(void)
{
    int err = pthread_rwlock_wrlock(&rwlock_shared);
    if (err != 0)
        stm_fatalerror("start_exclusivelock: "
                       "pthread_rwlock_wrlock failure\n");
    dprintf(("start_exclusivelock\n"));
}

static void stop_exclusivelock(void)
{
    dprintf(("stop_exclusivelock\n"));
    int err = pthread_rwlock_unlock(&rwlock_shared);
    if (err != 0)
        stm_fatalerror("stop_exclusivelock: "
                       "pthread_rwlock_unlock failure\n");
}

void stm_start_single_thread(void)
{
    /* Called by the GC, just after a minor collection, when we need to do
       a major collection.  When it returns, it acquired the "write lock"
       which prevents any other thread from running in a transaction.
       Warning, may block waiting for rwlock_in_transaction while another
       thread runs a major GC itself! */
    ACCESS_ONCE(sync_required) = -1;
    stm_stop_sharedlock();
    start_exclusivelock();
    ACCESS_ONCE(sync_required) = 0;

    assert(in_single_thread == NULL);
    in_single_thread = thread_descriptor;
    assert(in_single_thread != NULL);
}

void stm_stop_single_thread(void)
{
    /* Warning, may block waiting for rwlock_in_transaction while another
       thread runs a major GC */
    assert(in_single_thread == thread_descriptor);
    in_single_thread = NULL;

    stop_exclusivelock();
    stm_start_sharedlock();
}

void stm_possible_safe_point(void)
{
    if (!ACCESS_ONCE(sync_required))
        return;

    /* Warning, may block waiting for rwlock_in_transaction while another
       thread runs a major GC */
    assert(thread_descriptor->active);
    assert(in_single_thread != thread_descriptor);

    stm_stop_sharedlock();
    /* another thread should be waiting in start_exclusivelock(),
       which takes priority here */
    stm_start_sharedlock();

    AbortNowIfDelayed();   /* if another thread ran a major GC */
}

void stm_minor_collect(void)
{
    stmgc_minor_collect();
    stmgcpage_possibly_major_collect(0);
}

void stm_major_collect(void)
{
    stmgc_minor_collect();
    stmgcpage_possibly_major_collect(1);
}

/************************************************************/

/***** Prebuilt roots, added in the list as the transaction that changed
       them commits *****/

struct GcPtrList stm_prebuilt_gcroots = {0};

void stm_add_prebuilt_root(gcptr obj)
{
    assert(obj->h_tid & GCFLAG_PREBUILT_ORIGINAL);
    gcptrlist_insert(&stm_prebuilt_gcroots, obj);
}

void stm_clear_between_tests(void)
{
    dprintf(("\n"
            "===============================================================\n"
            "========================[  START  ]============================\n"
            "===============================================================\n"
            "\n"));
    gcptrlist_clear(&stm_prebuilt_gcroots);
}
