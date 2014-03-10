#ifndef __PYPY_THREAD_H
#define __PYPY_THREAD_H
#include <assert.h>

#define RPY_TIMEOUT_T long long

typedef enum RPyLockStatus {
    RPY_LOCK_FAILURE = 0,
    RPY_LOCK_ACQUIRED = 1,
    RPY_LOCK_INTR = 2
} RPyLockStatus;

#ifdef _WIN32
#include "thread_nt.h"
#else

/* We should check if unistd.h defines _POSIX_THREADS, but sometimes
   it is not defined even though the system implements them as an
   external library (e.g. gnu pth in pthread emulation).  So we just
   always go ahead and use them, assuming they are supported on all
   platforms for which we care.  If not, do some detecting again.
*/
#include "thread_pthread.h"

#endif /* !_WIN32 */


void RPyGilYieldThread(void);
void RPyGilAcquire(void);

extern void *rpy_fastgil;

static inline void RPyGilRelease(void) {
    assert(rpy_fastgil == NULL);
    rpy_fastgil = (void *)1;
}
static inline void *RPyFetchFastGil(void) {
    return &rpy_fastgil;
}

#endif
