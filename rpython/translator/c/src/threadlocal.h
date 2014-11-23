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

#define OP_THREADLOCALREF_ADDR(r)                       \
    do {                                                \
        RPyAssert(pypy_threadlocal.ready == 42,         \
                  "uninitialized thread-local!");       \
        r = (char *)&pypy_threadlocal;                  \
    } while (0)

#define OP_THREADLOCALREF_MAKE(r)               \
    do {                                        \
        r = (char *)&pypy_threadlocal;          \
        if (pypy_threadlocal.ready != 42)       \
            r = _RPython_ThreadLocals_Build();  \
    } while (0)


/* ------------------------------------------------------------ */
#elif _WIN32
/* ------------------------------------------------------------ */


#include <WinSock2.h>
#include <windows.h>

RPY_EXTERN DWORD pypy_threadlocal_key;
#define OP_THREADLOCALREF_ADDR(r)    r = (char *)TlsGetValue(  \
                                           pypy_threadlocal_key)
#define OP_THREADLOCALREF_MAKE(r)                       \
    (OP_THREADLOCALREF_ADDR(r),                         \
     ((r) || (r = _RPython_ThreadLocals_Build())))


/* ------------------------------------------------------------ */
#else
/* ------------------------------------------------------------ */


/* Other POSIX systems: use the pthread API */

#include <pthread.h>

RPY_EXTERN pthread_key_t pypy_threadlocal_key;
#define OP_THREADLOCALREF_ADDR(r)    r = (char *)pthread_getspecific(  \
                                           pypy_threadlocal_key)
#define OP_THREADLOCALREF_MAKE(r)                       \
    (OP_THREADLOCALREF_ADDR(r),                         \
     ((r) || (r = _RPython_ThreadLocals_Build())))


/* ------------------------------------------------------------ */
#endif
/* ------------------------------------------------------------ */


#endif /* _SRC_THREADLOCAL_H */
