#include <pthread.h>
#include <stdlib.h>
#include <assert.h>
#include <stdbool.h>
#include "threadlocal.h"

static pthread_mutex_t master_mutex;
static pthread_mutex_t sync_mutex;
static pthread_cond_t  sync_cond;

static long counter_of_sevens = 0;

static long rpy_initialize = -42;


static void rpy_init_mutexes(void)
{
    int err = pthread_mutex_init(&master_mutex, NULL);
    if (err)
        abort();

    err = pthread_mutex_init(&sync_mutex, NULL);
    if (err)
        abort();

    err = pthread_cond_init(&sync_cond, NULL);
    if (err)
        abort();

    counter_of_sevens = 0; // XXX: fork?
    rpy_initialize = 0;
}

void RPyGilAllocate(void)
{
    if (rpy_initialize < 0) {
        assert(rpy_initialize == -42);
        rpy_init_mutexes();
#ifdef HAVE_PTHREAD_ATFORK
        pthread_atfork(NULL, NULL, rpy_init_mutexes);
#endif
    }
}


void RPyGilAcquireSlowPath(void)
{
    /* wait until the master leaves the safe point */
    pthread_mutex_lock(&master_mutex);

    long synclock = RPY_THREADLOCALREF_GET(synclock);
    assert(synclock == 0b110 || synclock == 0b000);

    bool is_new_thread = synclock == 000;
    if (is_new_thread) {
        // TODO: do the shadowstack.py:allocate_shadow_stack() here, then the
        // walk_thread_stack() does not need to check for ss_top==NULL anymore.
    }

    RPY_THREADLOCALREF_GET(synclock) = 0b101L;
    pthread_mutex_unlock(&master_mutex);
}

void RPyGilReleaseSlowPath(void)
{
    pthread_mutex_lock(&sync_mutex);
    assert(RPY_THREADLOCALREF_GET(synclock) == 0b111L);

    /* we are one of the SEVENs that the master is waiting for. Decrease the
     * counter and signal the master if we are the last. */
    counter_of_sevens--;
    if (counter_of_sevens == 0)
        pthread_cond_signal(&sync_cond);

    /* set to 110, so that Acquire above will wait until the master is finished
     * with its safe point */
    RPY_THREADLOCALREF_GET(synclock) = 0b110L;
    pthread_mutex_unlock(&sync_mutex);
    // continue without GIL
}

void RPyGilYieldThreadSlowPath(void)
{
    RPyGilRelease();
    RPyGilAcquire();
}

void RPyGilEnterMasterSection(void)
{
    RPyGilRelease();
    pthread_mutex_lock(&master_mutex);
}

void RPyGilLeaveMasterSection(void)
{
    pthread_mutex_unlock(&master_mutex);
    RPyGilAcquire();
}

__attribute__((no_sanitize_thread))
void RPyGilMasterRequestSafepoint(void)
{
    pthread_mutex_lock(&sync_mutex);
    assert(counter_of_sevens == 0);

    /* signal all threads to enter safepoints */
    OP_THREADLOCALREF_ACQUIRE(/* */);

    struct pypy_threadlocal_s *t = NULL;
    while (1) {
        OP_THREADLOCALREF_ENUM(t, t);
        if (t == NULL)
            break;

      retry:;
        /* this read and the setting of nursery_top make thread sanitizer
         * unhappy */
        long synclock = t->synclock;
        switch (synclock) {
        default:
            fprintf(stderr, "ERROR: found synclock=%ld\n", synclock);
            abort();
        case 0b000L:
            /* new thread, no need to explicitly request safepoint */
            break;
        case 0b110L:
            /* thread running in C code, already knows we want a safepoint */
            break;
        case 0b100L:
            /* thread running in C code, make sure it checks for and enters
             * the safepoint before acquiring the "gil" again */
            if (__sync_bool_compare_and_swap(&t->synclock, 0b100L, 0b110L))
                break;
            goto retry;
        case 0b101L:
            /* thread running normally, place request to enter safepoint */
            if (__sync_bool_compare_and_swap(&t->synclock, 0b101L, 0b111L)) {
                counter_of_sevens++;
                t->nursery_top = NULL;
                break;
            }
            goto retry;
        }
    }
    OP_THREADLOCALREF_RELEASE(/* */);

    /* wait until all SEVENs entered their safepoints */
    while (counter_of_sevens > 0) {
        pthread_cond_wait(&sync_cond, &sync_mutex);
    }

    pthread_mutex_unlock(&sync_mutex);

    /* caller can continue; all threads in safepoints */
}

/********** for tests only **********/

/* These functions are usually defined as a macros RPyXyz() in thread.h
   which get translated into calls to _RpyXyz().  But for tests we need
   the real functions to exists in the library as well.
*/

#undef RPyGilRelease
RPY_EXTERN
void RPyGilRelease(void)
{
    /* Releases the GIL in order to do an external function call.
       We assume that the common case is that the function call is
       actually very short, and optimize accordingly.
    */
    _RPyGilRelease();
}

#undef RPyGilAcquire
RPY_EXTERN
void RPyGilAcquire(void)
{
    _RPyGilAcquire();
}

#undef RPyFetchFastGil
RPY_EXTERN
long *RPyFetchFastGil(void)
{
    return _RPyFetchFastGil();
}
