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
RPY_EXTERN long RPyGilYieldThread(void);
RPY_EXTERN void RPyGilAcquireSlowPath(long);
#define RPyGilAcquire _RPyGilAcquire
#define RPyGilRelease _RPyGilRelease
#define RPyFetchFastGil _RPyFetchFastGil

#ifdef PYPY_USE_ASMGCC
# define RPY_FASTGIL_LOCKED(x)   (x == 1)
#else
# define RPY_FASTGIL_LOCKED(x)   (x != 0)
#endif

//RPY_EXTERN long rpy_fastgil;

static inline void _RPyGilAcquire(void) {
//    long old_fastgil = pypy_lock_test_and_set(&rpy_fastgil, 1);
//    if (old_fastgil != 0)
//        RPyGilAcquireSlowPath(old_fastgil);
}
static inline void _RPyGilRelease(void) {
//    assert(RPY_FASTGIL_LOCKED(rpy_fastgil));
//    pypy_lock_release(&rpy_fastgil);
}
static inline long *_RPyFetchFastGil(void) {
    abort();
//    return &rpy_fastgil;
}

#endif
