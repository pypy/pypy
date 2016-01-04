#include "common_header.h"
#include "structdef.h"       /* for struct pypy_threadlocal_s */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "src/threadlocal.h"


pthread_key_t pypy_threadlocal_key
#ifdef _WIN32
= TLS_OUT_OF_INDEXES
#endif
;

static struct pypy_threadlocal_s linkedlist_head = {
    -1,                     /* ready     */
    NULL,                   /* stack_end */
    &linkedlist_head,       /* prev      */
    &linkedlist_head };     /* next      */

struct pypy_threadlocal_s *
_RPython_ThreadLocals_Enum(struct pypy_threadlocal_s *prev)
{
    if (prev == NULL)
        prev = &linkedlist_head;
    if (prev->next == &linkedlist_head)
        return NULL;
    return prev->next;
}

static void _RPy_ThreadLocals_Init(void *p)
{
    struct pypy_threadlocal_s *tls = (struct pypy_threadlocal_s *)p;
    struct pypy_threadlocal_s *oldnext;
    memset(p, 0, sizeof(struct pypy_threadlocal_s));

#ifdef RPY_TLOFS_p_errno
    tls->p_errno = &errno;
#endif
#ifdef RPY_TLOFS_thread_ident
    tls->thread_ident =
#    ifdef _WIN32
        GetCurrentThreadId();
#    else
        (long)pthread_self();    /* xxx This abuses pthread_self() by
                  assuming it just returns a integer.  According to
                  comments in CPython's source code, the platforms
                  where it is not the case are rather old nowadays. */
#    endif
#endif
    oldnext = linkedlist_head.next;
    tls->prev = &linkedlist_head;
    tls->next = oldnext;
    linkedlist_head.next = tls;
    oldnext->prev = tls;
    tls->ready = 42;
}

static void threadloc_unlink(void *p)
{
    struct pypy_threadlocal_s *tls = (struct pypy_threadlocal_s *)p;
    if (tls->ready == 42) {
        tls->ready = 0;
        tls->next->prev = tls->prev;
        tls->prev->next = tls->next;
        memset(tls, 0xDD, sizeof(struct pypy_threadlocal_s));  /* debug */
    }
#ifndef USE___THREAD
    free(p);
#endif
}

#ifdef _WIN32
/* xxx Defines a DllMain() function.  It's horrible imho: it only
   works if we happen to compile a DLL (not a EXE); and of course you
   get link-time errors if two files in the same DLL do the same.
   There are some alternatives known, but they are horrible in other
   ways (e.g. using undocumented behavior).  This seems to be the
   simplest, but feel free to fix if you need that.
 */
BOOL WINAPI DllMain(HINSTANCE hinstDLL,
                    DWORD     reason_for_call,
                    LPVOID    reserved)
{
    LPVOID p;
    switch (reason_for_call) {
    case DLL_THREAD_DETACH:
        if (pypy_threadlocal_key != TLS_OUT_OF_INDEXES) {
            p = TlsGetValue(pypy_threadlocal_key);
            if (p != NULL) {
                TlsSetValue(pypy_threadlocal_key, NULL);
                threadloc_unlink(p);
            }
        }
        break;
    default:
        break;
    }
    return TRUE;
}
#endif

void RPython_ThreadLocals_ProgramInit(void)
{
    /* Initialize the pypy_threadlocal_key, together with a destructor
       that will be called every time a thread shuts down (if there is
       a non-null thread-local value).  This is needed even in the
       case where we use '__thread' below, for the destructor.
    */
#ifdef _WIN32
    pypy_threadlocal_key = TlsAlloc();
    if (pypy_threadlocal_key == TLS_OUT_OF_INDEXES)
#else
    if (pthread_key_create(&pypy_threadlocal_key, threadloc_unlink) != 0)
#endif
    {
        fprintf(stderr, "Internal RPython error: "
                        "out of thread-local storage indexes");
        abort();
    }
    _RPython_ThreadLocals_Build();
}


/* ------------------------------------------------------------ */
#ifdef USE___THREAD
/* ------------------------------------------------------------ */


/* in this situation, we always have one full 'struct pypy_threadlocal_s'
   available, managed by gcc. */
__thread struct pypy_threadlocal_s pypy_threadlocal;

char *_RPython_ThreadLocals_Build(void)
{
    RPyAssert(pypy_threadlocal.ready == 0, "corrupted thread-local");
    _RPy_ThreadLocals_Init(&pypy_threadlocal);

    /* we also set up &pypy_threadlocal as a POSIX thread-local variable,
       because we need the destructor behavior. */
    pthread_setspecific(pypy_threadlocal_key, (void *)&pypy_threadlocal);

    return (char *)&pypy_threadlocal;
}

void RPython_ThreadLocals_ThreadDie(void)
{
    pthread_setspecific(pypy_threadlocal_key, NULL);
    threadloc_unlink(&pypy_threadlocal);
}


/* ------------------------------------------------------------ */
#else
/* ------------------------------------------------------------ */


/* this is the case where the 'struct pypy_threadlocal_s' is allocated
   explicitly, with malloc()/free(), and attached to (a single) thread-
   local key using the API of Windows or pthread. */


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
        threadloc_unlink(p);   /* includes free(p) */
    }
}


/* ------------------------------------------------------------ */
#endif
/* ------------------------------------------------------------ */
