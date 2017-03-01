#ifndef __PYPY_THREAD_H
#define __PYPY_THREAD_H
#include "precommondefs.h"
#include <assert.h>
#include <stdlib.h>

#define RPY_TIMEOUT_T long long

typedef enum RPyLockStatus {
    RPY_LOCK_FAILURE = 0,
    RPY_LOCK_ACQUIRED = 1,
    RPY_LOCK_INTR = 2
} RPyLockStatus;

#ifdef _WIN32
#define RPYTHREAD_NAME "nt"
#include "thread_nt.h"
#define inline _inline
#else

/* We should check if unistd.h defines _POSIX_THREADS, but sometimes
   it is not defined even though the system implements them as an
   external library (e.g. gnu pth in pthread emulation).  So we just
   always go ahead and use them, assuming they are supported on all
   platforms for which we care.  If not, do some detecting again.
*/
#define RPYTHREAD_NAME "pthread"
#include "thread_pthread.h"

#endif /* !_WIN32 */

RPY_EXTERN void RPyGilAllocate(void);
RPY_EXTERN void RPyGilYieldThreadSlowPath(void);
RPY_EXTERN void RPyGilAcquireSlowPath(void);
RPY_EXTERN void RPyGilReleaseSlowPath(void);

RPY_EXTERN void RPyGilEnterMasterSection(void);
RPY_EXTERN void RPyGilLeaveMasterSection(void);
RPY_EXTERN void RPyGilMasterRequestSafepoint(void);


#define RPyGilAcquire _RPyGilAcquire
#define RPyGilRelease _RPyGilRelease
#define RPyFetchFastGil _RPyFetchFastGil

#ifdef PYPY_USE_ASMGCC
# define RPY_FASTGIL_LOCKED(x)   (x == 1)
#else
# define RPY_FASTGIL_LOCKED(x)   (x != 0)
#endif

//RPY_EXTERN long rpy_fastgil;
#include "threadlocal.h"

#define _RPyGilAcquire() do { \
        if (!__sync_bool_compare_and_swap(                  \
                &RPY_THREADLOCALREF_GET(synclock), 0L, 1L)) \
            RPyGilAcquireSlowPath();                        \
    } while (0)

#define _RPyGilRelease() do { \
        assert(RPY_THREADLOCALREF_GET(synclock) != 0L); \
    if (!__sync_bool_compare_and_swap(                  \
            &RPY_THREADLOCALREF_GET(synclock), 1L, 0L)) \
        RPyGilReleaseSlowPath();                        \
    } while (0)

static inline long *_RPyFetchFastGil(void) {
    abort();
//    return &rpy_fastgil;
}

#define RPyGilYieldThread() do { \
    assert(RPY_THREADLOCALREF_GET(synclock) & 1L); \
    if (RPY_THREADLOCALREF_GET(synclock) == 3L) { \
        RPyGilYieldThreadSlowPath(); \
    } \
    } while (0)

typedef unsigned char rpy_spinlock_t;
static inline void rpy_spinlock_acquire(rpy_spinlock_t *p)
{
    while (pypy_lock_test_and_set(p, 1) != 0)
        pypy_spin_loop();
}
static inline void rpy_spinlock_release(rpy_spinlock_t *p)
{
    pypy_lock_release(p);
}

#endif
