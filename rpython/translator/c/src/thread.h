#ifndef __PYPY_THREAD_H
#define __PYPY_THREAD_H
#include "precommondefs.h"
#include <assert.h>

#define RPY_TIMEOUT_T long long

typedef enum RPyLockStatus {
    RPY_LOCK_FAILURE = 0,
    RPY_LOCK_ACQUIRED = 1,
    RPY_LOCK_INTR = 2
} RPyLockStatus;

#ifdef _WIN32
#include "thread_nt.h"
#define inline _inline
#else

/* We should check if unistd.h defines _POSIX_THREADS, but sometimes
   it is not defined even though the system implements them as an
   external library (e.g. gnu pth in pthread emulation).  So we just
   always go ahead and use them, assuming they are supported on all
   platforms for which we care.  If not, do some detecting again.
*/
#include "thread_pthread.h"

#endif /* !_WIN32 */

RPY_EXTERN void RPyGilAllocate(void);
RPY_EXTERN long RPyGilYieldThread(void);
RPY_EXTERN void RPyGilAcquire(void);
#define RPyGilRelease _RPyGilRelease
#define RPyFetchFastGil _RPyFetchFastGil

#ifdef PYPY_USE_ASMGCC
# define RPY_FASTGIL_LOCKED(x)   (x == 1)
#else
# define RPY_FASTGIL_LOCKED(x)   (x != 0)
#endif

RPY_EXTERN long rpy_fastgil;

static inline void _RPyGilRelease(void) {
    assert(RPY_FASTGIL_LOCKED(rpy_fastgil));
    rpy_fastgil = 0;
}
static inline long *_RPyFetchFastGil(void) {
    return &rpy_fastgil;
}

#endif
