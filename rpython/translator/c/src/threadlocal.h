/* Thread-local storage */
#ifndef _SRC_THREADLOCAL_H
#define _SRC_THREADLOCAL_H

#include <src/precommondefs.h>


#ifndef RPY_HAS_THREADLOCAL_S
#  error "src/threadlocal.h should only be included if RPY_HAS_THREADLOCAL_S"
#endif


/* ------------------------------------------------------------ */
#ifdef USE___THREAD
/* ------------------------------------------------------------ */


/* Use the '__thread' specifier, so far only on Linux */

RPY_EXTERN __thread struct pypy_threadlocal_s pypy_threadlocal;
#define OP_THREADLOCALREF_ADDR(r)    r = (char *)&pypy_threadlocal


/* ------------------------------------------------------------ */
#elif _WIN32
/* ------------------------------------------------------------ */


#include <WinSock2.h>
#include <windows.h>

RPY_EXTERN DWORD pypy_threadlocal_key;
#define OP_THREADLOCALREF_ADDR(r)    r = (char *)TlsGetValue(  \
                                           pypy_threadlocal_key)


/* ------------------------------------------------------------ */
#else
/* ------------------------------------------------------------ */


/* Other POSIX systems: use the pthread API */

#include <pthread.h>

RPY_EXTERN pthread_key_t pypy_threadlocal_key;
#define OP_THREADLOCALREF_ADDR(r)    r = (char *)pthread_getspecific(  \
                                           pypy_threadlocal_key)


/* ------------------------------------------------------------ */
#endif
/* ------------------------------------------------------------ */


RPY_EXTERN void RPython_ThreadLocals_ProgramInit(void);
RPY_EXTERN void RPython_ThreadLocals_ThreadStart(void);
RPY_EXTERN void RPython_ThreadLocals_ThreadDie(void);

#endif /* _SRC_THREADLOCAL_H */
