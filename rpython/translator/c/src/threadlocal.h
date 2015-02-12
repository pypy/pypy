/* Thread-local storage */
#ifndef _SRC_THREADLOCAL_H
#define _SRC_THREADLOCAL_H

#include "src/precommondefs.h"
#include "src/support.h"


/* RPython_ThreadLocals_ProgramInit() is called once at program start-up. */
RPY_EXTERN void RPython_ThreadLocals_ProgramInit(void);

/* RPython_ThreadLocals_ThreadDie() is called in a thread that is about
   to die. */
RPY_EXTERN void RPython_ThreadLocals_ThreadDie(void);

/* There are two llops: 'threadlocalref_addr' and 'threadlocalref_make'.
   They both return the address of the thread-local structure (of the
   C type 'struct pypy_threadlocal_s').  The difference is that
   OP_THREADLOCALREF_MAKE() checks if we have initialized this thread-
   local structure in the current thread, and if not, calls the following
   helper. */
RPY_EXTERN char *_RPython_ThreadLocals_Build(void);


/* ------------------------------------------------------------ */
#ifdef USE___THREAD
/* ------------------------------------------------------------ */


/* Use the '__thread' specifier, so far only on Linux */

RPY_EXTERN __thread struct pypy_threadlocal_s pypy_threadlocal;

#define OP_THREADLOCALREF_ADDR(r)               \
    do {                                        \
        r = (char *)&pypy_threadlocal;          \
        if (pypy_threadlocal.ready != 42)       \
            r = _RPython_ThreadLocals_Build();  \
    } while (0)

#define RPY_THREADLOCALREF_ENSURE()             \
    if (pypy_threadlocal.ready != 42)           \
        (void)_RPython_ThreadLocals_Build();

#define RPY_THREADLOCALREF_GET(FIELD)   pypy_threadlocal.FIELD


/* ------------------------------------------------------------ */
#else
/* ------------------------------------------------------------ */


/* Don't use '__thread'. */

#ifdef _WIN32
#  include <WinSock2.h>
#  include <windows.h>
#  define _RPy_ThreadLocals_Get()   TlsGetValue(pypy_threadlocal_key)
#  define _RPy_ThreadLocals_Set(x)  TlsSetValue(pypy_threadlocal_key, x)
typedef DWORD pthread_key_t;
#else
#  include <pthread.h>
#  define _RPy_ThreadLocals_Get()   pthread_getspecific(pypy_threadlocal_key)
#  define _RPy_ThreadLocals_Set(x)  pthread_setspecific(pypy_threadlocal_key, x)
#endif

RPY_EXTERN pthread_key_t pypy_threadlocal_key;


#define OP_THREADLOCALREF_ADDR(r)               \
    do {                                        \
        r = (char *)_RPy_ThreadLocals_Get();    \
        if (!r)                                 \
            r = _RPython_ThreadLocals_Build();  \
    } while (0)

#define RPY_THREADLOCALREF_ENSURE()             \
    if (!_RPy_ThreadLocals_Get())               \
        (void)_RPython_ThreadLocals_Build();

#define RPY_THREADLOCALREF_GET(FIELD)           \
    ((struct pypy_threadlocal_s *)_RPy_ThreadLocals_Get())->FIELD


/* ------------------------------------------------------------ */
#endif
/* ------------------------------------------------------------ */


/* only for the fall-back path in the JIT */
#define OP_THREADLOCALREF_GET_NONCONST(RESTYPE, offset, r)      \
    do {                                                        \
        char *a;                                                \
        OP_THREADLOCALREF_ADDR(a);                              \
        r = *(RESTYPE *)(a + offset);                           \
    } while (0)


#endif /* _SRC_THREADLOCAL_H */
