/* Thread implementation */
#include "src/thread.h"

#ifdef PYPY_USING_BOEHM_GC
/* The following include is required by the Boehm GC, which apparently
 * crashes when pthread_create_thread() is not redefined to call a
 * Boehm wrapper function instead.  Ugly.
 */
#include "common_header.h"
#endif

#ifdef RPYTHON_LL2CTYPES
// only for python tests

#define RPY_TLOFS_alt_errno  offsetof(struct pypy_threadlocal_s, alt_errno)
#define RPY_TLOFS_nursery_free  offsetof(struct pypy_threadlocal_s, nursery_free)
#define RPY_TLOFS_nursery_top  offsetof(struct pypy_threadlocal_s, nursery_top)
#define RPY_TLOFS_rpy_errno  offsetof(struct pypy_threadlocal_s, rpy_errno)
#define RPY_TLOFS_shadowstack  offsetof(struct pypy_threadlocal_s, shadowstack)
#define RPY_TLOFS_shadowstack_top  offsetof(struct pypy_threadlocal_s, shadowstack_top)
#define RPY_TLOFS_synclock  offsetof(struct pypy_threadlocal_s, synclock)
struct pypy_threadlocal_s {
    int ready;
    char *stack_end;
    struct pypy_threadlocal_s *prev, *next;
    int alt_errno;
    void* nursery_free;
    void* nursery_top;
    int rpy_errno;
    void* shadowstack;
    void* shadowstack_top;
    Signed synclock;
};

/* only for testing: ll2ctypes sets RPY_EXTERN from the command-line */
#ifndef RPY_EXTERN
#define RPY_EXTERN RPY_EXPORTED
#endif

#define USE__THREAD 1

/* RPY_EXTERN __thread struct pypy_threadlocal_s pypy_threadlocal = { 0 }; */

#include "threadlocal.c"

#else

# include "common_header.h"
# include "structdef.h"
# include "forwarddecl.h"

#endif


#ifdef _WIN32
#include "src/thread_nt.c"
#else
#include "src/thread_pthread.c"
#endif
