#include "common_header.h"
#include "structdef.h"

#ifdef RPY_HAS_THREADLOCAL_S     /* otherwise, this file is not needed */

#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include "src/threadlocal.h"
#include "src/thread.h"


static void _RPython_ThreadLocals_Init(char *p)
{
    struct pypy_threadlocal_s *tl = (struct pypy_threadlocal_s *)p;
#ifdef RPY_TLOFS_p_errno
    tl->p_errno = &errno;
#endif
#ifdef RPY_TLOFS_thread_ident
    tl->thread_ident = RPyThreadGetIdent();
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
    char *p = malloc(sizeof(struct pypy_threadlocal_s));
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
    char *p;
    OP_THREADLOCALREF_ADDR(p);
    free(p);
}


/* ------------------------------------------------------------ */
#endif
/* ------------------------------------------------------------ */


#endif  /* RPY_HAS_THREADLOCAL_S */
