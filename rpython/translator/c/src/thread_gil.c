#include <pthread.h>
#include <stdlib.h>
#include <assert.h>
#include "threadlocal.h"

static pthread_mutex_t master_mutex;
static pthread_mutex_t sync_mutex;
static pthread_cond_t  sync_cond;

static long counter_of_threes = 0;

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

    counter_of_threes = 0; // XXX: fork?
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
    assert(RPY_THREADLOCALREF_GET(synclock) == 2);

    /* wait until the master leaves the safe point */
    pthread_mutex_lock(&master_mutex);
    RPY_THREADLOCALREF_GET(synclock) = 1;
    pthread_mutex_unlock(&master_mutex);
}

void RPyGilReleaseSlowPath(void)
{
    assert(RPY_THREADLOCALREF_GET(synclock) == 3);

    pthread_mutex_lock(&sync_mutex);

    /* we are one of the THREES that the master is waiting for. Decrease the
     * counter and signal the master if we are the last. */
    counter_of_threes--;
    if (counter_of_threes == 0)
        pthread_cond_signal(&sync_cond);

    /* set to TWO, so that Acquire above will wait until the master is finished
     * with its safe point */
    RPY_THREADLOCALREF_GET(synclock) = 2;
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

void RPyGilMasterRequestSafepoint(void)
{
    pthread_mutex_lock(&sync_mutex);
    assert(counter_of_threes == 0);

    /* signal all threads to enter safepoints */
    OP_THREADLOCALREF_ACQUIRE(/* */);

    struct pypy_threadlocal_s *t = NULL;
    while (1) {
        OP_THREADLOCALREF_ENUM(t, t);
        if (t == NULL)
            break;

      retry:
        switch (t->synclock) {
        case 3:
            assert(!"unexpected synclock=3 found");
            abort();
        case 2:
            /* thread running in C code, already knows we want a safepoint */
            break;
        case 0:
            /* thread running in C code, make sure it checks for and enters
             * the safepoint before acquiring the "gil" again */
            if (__sync_bool_compare_and_swap(&t->synclock, 0, 2))
                break;
            goto retry;
        case 1:
            /* thread running normally, place request to enter safepoint */
            if (__sync_bool_compare_and_swap(&t->synclock, 1, 3)) {
                counter_of_threes++;
                t->nursery_top = NULL;
                break;
            }
            goto retry;
        }
    }
    OP_THREADLOCALREF_RELEASE(/* */);

    /* wait until all THREES entered their safepoints */
    while (counter_of_threes > 0) {
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
