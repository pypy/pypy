#include <Python.h>
#include "src/thread.h"

long
PyThread_get_thread_ident(void)
{
#ifdef _WIN32
    return (long)GetCurrentThreadId();
#else
    return (long)pthread_self();
#endif
}

static int initialized;

void
PyThread_init_thread(void)
{
    if (initialized)
        return;
    initialized = 1;
    /*PyThread__init_thread(); a NOP on modern platforms */
}

PyThread_type_lock
PyThread_allocate_lock(void)
{
    struct RPyOpaque_ThreadLock *lock;
    lock = malloc(sizeof(struct RPyOpaque_ThreadLock));
    if (lock == NULL)
        return NULL;

    if (RPyThreadLockInit(lock) == 0) {
        free(lock);
        return NULL;
    }

    return (PyThread_type_lock)lock;
}

void
PyThread_free_lock(PyThread_type_lock lock)
{
    struct RPyOpaque_ThreadLock *real_lock = lock;
    RPyThreadAcquireLock(real_lock, 0);
    RPyThreadReleaseLock(real_lock);
    RPyOpaqueDealloc_ThreadLock(real_lock);
    free(lock);
}

int
PyThread_acquire_lock(PyThread_type_lock lock, int waitflag)
{
    return RPyThreadAcquireLock((struct RPyOpaque_ThreadLock*)lock, waitflag);
}

void
PyThread_release_lock(PyThread_type_lock lock)
{
    RPyThreadReleaseLock((struct RPyOpaque_ThreadLock*)lock);
}

long
PyThread_start_new_thread(void (*func)(void *), void *arg)
{
    PyThread_init_thread();
    return RPyThreadStartEx(func, arg);
}

