#include "common_header.h"
#include "structdef.h"       /* for struct pypy_threadlocal_s */
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include "src/threadlocal.h"


#ifdef _WIN32
#  define RPyThreadGetIdent() GetCurrentThreadId()
#else
#  define RPyThreadGetIdent() ((long)pthread_self())
/* xxx This abuses pthread_self() by assuming it just returns a long.
   According to comments in CPython's source code, the platforms where
   it is wrong are rather old nowadays. */
#endif


static void _RPython_ThreadLocals_Init(void *p)
{
    memset(p, 0, sizeof(struct pypy_threadlocal_s));
#ifdef RPY_TLOFS_p_errno
    ((struct pypy_threadlocal_s *)p)->p_errno = &errno;
#endif
#ifdef RPY_TLOFS_thread_ident
    ((struct pypy_threadlocal_s *)p)->thread_ident = RPyThreadGetIdent();
#endif
}


/* ------------------------------------------------------------ */
#ifdef USE___THREAD
/* ------------------------------------------------------------ */


__thread struct pypy_threadlocal_s pypy_threadlocal;

void RPython_ThreadLocals_ProgramInit(void)
{
    RPython_ThreadLocals_ThreadStart();
}

void RPython_ThreadLocals_ThreadStart(void)
{
    _RPython_ThreadLocals_Init(&pypy_threadlocal);
}

void RPython_ThreadLocals_ThreadDie(void)
{
}


/* ------------------------------------------------------------ */
#else
/* ------------------------------------------------------------ */


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
    RPython_ThreadLocals_ThreadStart();
}

void RPython_ThreadLocals_ThreadStart(void)
{
    void *p = malloc(sizeof(struct pypy_threadlocal_s));
    if (!p) {
        fprintf(stderr, "Internal RPython error: "
                        "out of memory for the thread-local storage");
        abort();
    }
    _RPython_ThreadLocals_Init(p);
#ifdef _WIN32
    TlsSetValue(pypy_threadlocal_key, p);
#else
    pthread_setspecific(pypy_threadlocal_key, p);
#endif
}

void RPython_ThreadLocals_ThreadDie(void)
{
    void *p;
    OP_THREADLOCALREF_ADDR(p);
    free(p);
}


/* ------------------------------------------------------------ */
#endif
/* ------------------------------------------------------------ */
