#include "common_header.h"
#include "structdef.h"       /* for struct pypy_threadlocal_s */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef _WIN32
# include <pthread.h>
#endif
#include "src/threadlocal.h"


static void _RPy_ThreadLocals_Init(void *p)
{
    memset(p, 0, sizeof(struct pypy_threadlocal_s));
#ifdef RPY_TLOFS_p_errno
    ((struct pypy_threadlocal_s *)p)->p_errno = &errno;
#endif
#ifdef RPY_TLOFS_thread_ident
    ((struct pypy_threadlocal_s *)p)->thread_ident =
#    ifdef _WIN32
        GetCurrentThreadId();
#    else
        (long)pthread_self();    /* xxx This abuses pthread_self() by
                  assuming it just returns a integer.  According to
                  comments in CPython's source code, the platforms
                  where it is not the case are rather old nowadays. */
#    endif
#endif
    ((struct pypy_threadlocal_s *)p)->ready = 42;
}


/* ------------------------------------------------------------ */
#ifdef USE___THREAD
/* ------------------------------------------------------------ */


/* in this situation, we always have one full 'struct pypy_threadlocal_s'
   available, managed by gcc. */
__thread struct pypy_threadlocal_s pypy_threadlocal;

void RPython_ThreadLocals_ProgramInit(void)
{
    _RPy_ThreadLocals_Init(&pypy_threadlocal);
}

char *_RPython_ThreadLocals_Build(void)
{
    RPyAssert(pypy_threadlocal.ready == 0, "corrupted thread-local");
    _RPy_ThreadLocals_Init(&pypy_threadlocal);
    return (char *)&pypy_threadlocal;
}

void RPython_ThreadLocals_ThreadDie(void)
{
    memset(&pypy_threadlocal, 0xDD,
           sizeof(struct pypy_threadlocal_s));  /* debug */
    pypy_threadlocal.ready = 0;
}


/* ------------------------------------------------------------ */
#else
/* ------------------------------------------------------------ */


/* this is the case where the 'struct pypy_threadlocal_s' is allocated
   explicitly, with malloc()/free(), and attached to (a single) thread-
   local key using the API of Windows or pthread. */

pthread_key_t pypy_threadlocal_key;


void RPython_ThreadLocals_ProgramInit(void)
{
#ifdef _WIN32
    pypy_threadlocal_key = TlsAlloc();
    if (pypy_threadlocal_key == TLS_OUT_OF_INDEXES)
#else
    if (pthread_key_create(&pypy_threadlocal_key, NULL) != 0)
#endif
    {
        fprintf(stderr, "Internal RPython error: "
                        "out of thread-local storage indexes");
        abort();
    }
    _RPython_ThreadLocals_Build();
}

char *_RPython_ThreadLocals_Build(void)
{
    void *p = malloc(sizeof(struct pypy_threadlocal_s));
    if (!p) {
        fprintf(stderr, "Internal RPython error: "
                        "out of memory for the thread-local storage");
        abort();
    }
    _RPy_ThreadLocals_Init(p);
    _RPy_ThreadLocals_Set(p);
    return (char *)p;
}

void RPython_ThreadLocals_ThreadDie(void)
{
    void *p = _RPy_ThreadLocals_Get();
    if (p != NULL) {
        _RPy_ThreadLocals_Set(NULL);
        memset(p, 0xDD, sizeof(struct pypy_threadlocal_s));  /* debug */
        free(p);
    }
}


/* ------------------------------------------------------------ */
#endif
/* ------------------------------------------------------------ */
