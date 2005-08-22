
/* #ifdef logic from CPython */

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
