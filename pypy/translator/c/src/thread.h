
/* #ifdef logic from CPython */

#ifndef __PYPY_THREAD_H
#define __PYPY_THREAD_H

#ifndef _POSIX_THREADS
/* This means pthreads are not implemented in libc headers, hence the macro
   not present in unistd.h. But they still can be implemented as an external
   library (e.g. gnu pth in pthread emulation) */
# ifdef HAVE_PTHREAD_H
#  include <pthread.h> /* _POSIX_THREADS */
# endif
#endif

#ifdef _POSIX_THREADS
#include "thread_pthread.h"
#endif

#ifdef NT_THREADS
#include "thread_nt.h"
#endif

#ifdef USE___THREAD

#define RPyThreadStaticTLS                  __thread void *
#define RPyThreadStaticTLS_Create(tls)      NULL
#define RPyThreadStaticTLS_Get(tls)         tls
#define RPyThreadStaticTLS_Set(tls, value)  tls = value

#endif

#ifndef RPyThreadStaticTLS

#define RPyThreadStaticTLS             RPyThreadTLS
#define RPyThreadStaticTLS_Create(key) RPyThreadTLS_Create(key)
#define RPyThreadStaticTLS_Get(key)    RPyThreadTLS_Get(key)
#define RPyThreadStaticTLS_Set(key, value) RPyThreadTLS_Set(key, value)

#endif

#endif
