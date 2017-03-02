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

/*
  synclock is 3 bits:
    bit 0: GIL acquired
    bit 1: safepoint requested
    bit 2: thread known and initialised (old)

  synclock possible values:
    000: new thread; GIL released; safepoint requested
    010: INVALID VALUE
    0?1: INVALID VALUE
    100: old thread; GIL released
    101: old thread; GIL acquired
    110: old thread; GIL released; safepoint requested
    111: old thread; GIL acquired; safepoint requested

  synclock transitions:
    acquire: (possible values: ??0)
      FASTPATH: 100 -> 101
      SLOWPATH: check safepoint; initialise new thread; ??? -> 101
    release: (possible values: 1?1):
      FASTPATH: 101 -> 100
      SLOWPATH: signal "now at safepoint"; 111 -> 110
 */

#define _RPyGilAcquire() do {                                           \
        assert((RPY_THREADLOCALREF_GET(synclock) & 0b001) == 0b0);      \
    if (!__sync_bool_compare_and_swap(                                  \
                &RPY_THREADLOCALREF_GET(synclock), 0b100L, 0b101L))     \
        RPyGilAcquireSlowPath();                                        \
        } while (0)

#define _RPyGilRelease() do {                                       \
        assert((RPY_THREADLOCALREF_GET(synclock) & 0b101) == 0b101);  \
    if (!__sync_bool_compare_and_swap(                              \
                &RPY_THREADLOCALREF_GET(synclock), 0b101L, 0b100L)) \
        RPyGilReleaseSlowPath();                                    \
        } while (0)

static inline long *_RPyFetchFastGil(void) {
    abort();
//    return &rpy_fastgil;
}

#define RPyGilYieldThread() do { \
    assert(RPY_THREADLOCALREF_GET(synclock) & 1L); \
    if (RPY_THREADLOCALREF_GET(synclock) == 0b111L) { \
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
