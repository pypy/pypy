#include <Python.h>
#ifndef _WIN32
# include <pthread.h>
#endif
#include "pythread.h"
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


/* ------------------------------------------------------------------------
Per-thread data ("key") support.

Use PyThread_create_key() to create a new key.  This is typically shared
across threads.

Use PyThread_set_key_value(thekey, value) to associate void* value with
thekey in the current thread.  Each thread has a distinct mapping of thekey
to a void* value.  Caution:  if the current thread already has a mapping
for thekey, value is ignored.

Use PyThread_get_key_value(thekey) to retrieve the void* value associated
with thekey in the current thread.  This returns NULL if no value is
associated with thekey in the current thread.

Use PyThread_delete_key_value(thekey) to forget the current thread's associated
value for thekey.  PyThread_delete_key(thekey) forgets the values associated
with thekey across *all* threads.

While some of these functions have error-return values, none set any
Python exception.

None of the functions does memory management on behalf of the void* values.
You need to allocate and deallocate them yourself.  If the void* values
happen to be PyObject*, these functions don't do refcount operations on
them either.

The GIL does not need to be held when calling these functions; they supply
their own locking.  This isn't true of PyThread_create_key(), though (see
next paragraph).

There's a hidden assumption that PyThread_create_key() will be called before
any of the other functions are called.  There's also a hidden assumption
that calls to PyThread_create_key() are serialized externally.
------------------------------------------------------------------------ */

#ifdef MS_WINDOWS
#include <windows.h>

/* use native Windows TLS functions */
#define Py_HAVE_NATIVE_TLS

int
PyThread_create_key(void)
{
    return (int) TlsAlloc();
}

void
PyThread_delete_key(int key)
{
    TlsFree(key);
}

/* We must be careful to emulate the strange semantics implemented in thread.c,
 * where the value is only set if it hasn't been set before.
 */
int
PyThread_set_key_value(int key, void *value)
{
    BOOL ok;
    void *oldvalue;

    assert(value != NULL);
    oldvalue = TlsGetValue(key);
    if (oldvalue != NULL)
        /* ignore value if already set */
        return 0;
    ok = TlsSetValue(key, value);
    if (!ok)
        return -1;
    return 0;
}

void *
PyThread_get_key_value(int key)
{
    /* because TLS is used in the Py_END_ALLOW_THREAD macro,
     * it is necessary to preserve the windows error state, because
     * it is assumed to be preserved across the call to the macro.
     * Ideally, the macro should be fixed, but it is simpler to
     * do it here.
     */
    DWORD error = GetLastError();
    void *result = TlsGetValue(key);
    SetLastError(error);
    return result;
}

void
PyThread_delete_key_value(int key)
{
    /* NULL is used as "key missing", and it is also the default
     * given by TlsGetValue() if nothing has been set yet.
     */
    TlsSetValue(key, NULL);
}

/* reinitialization of TLS is not necessary after fork when using
 * the native TLS functions.  And forking isn't supported on Windows either.
 */
void
PyThread_ReInitTLS(void)
{}

#else  /* MS_WINDOWS */

/* A singly-linked list of struct key objects remembers all the key->value
 * associations.  File static keyhead heads the list.  keymutex is used
 * to enforce exclusion internally.
 */
struct key {
    /* Next record in the list, or NULL if this is the last record. */
    struct key *next;

    /* The thread id, according to PyThread_get_thread_ident(). */
    long id;

    /* The key and its associated value. */
    int key;
    void *value;
};

static struct key *keyhead = NULL;
static PyThread_type_lock keymutex = NULL;
static int nkeys = 0;  /* PyThread_create_key() hands out nkeys+1 next */

/* Internal helper.
 * If the current thread has a mapping for key, the appropriate struct key*
 * is returned.  NB:  value is ignored in this case!
 * If there is no mapping for key in the current thread, then:
 *     If value is NULL, NULL is returned.
 *     Else a mapping of key to value is created for the current thread,
 *     and a pointer to a new struct key* is returned; except that if
 *     malloc() can't find room for a new struct key*, NULL is returned.
 * So when value==NULL, this acts like a pure lookup routine, and when
 * value!=NULL, this acts like dict.setdefault(), returning an existing
 * mapping if one exists, else creating a new mapping.
 *
 * Caution:  this used to be too clever, trying to hold keymutex only
 * around the "p->next = keyhead; keyhead = p" pair.  That allowed
 * another thread to mutate the list, via key deletion, concurrent with
 * find_key() crawling over the list.  Hilarity ensued.  For example, when
 * the for-loop here does "p = p->next", p could end up pointing at a
 * record that PyThread_delete_key_value() was concurrently free()'ing.
 * That could lead to anything, from failing to find a key that exists, to
 * segfaults.  Now we lock the whole routine.
 */
static struct key *
find_key(int key, void *value)
{
    struct key *p, *prev_p;
    long id = PyThread_get_thread_ident();

    if (!keymutex)
        return NULL;
    PyThread_acquire_lock(keymutex, 1);
    prev_p = NULL;
    for (p = keyhead; p != NULL; p = p->next) {
        if (p->id == id && p->key == key)
            goto Done;
        /* Sanity check.  These states should never happen but if
         * they do we must abort.  Otherwise we'll end up spinning in
         * in a tight loop with the lock held.  A similar check is done
         * in pystate.c tstate_delete_common().  */
        if (p == prev_p)
            Py_FatalError("tls find_key: small circular list(!)");
        prev_p = p;
        if (p->next == keyhead)
            Py_FatalError("tls find_key: circular list(!)");
    }
    if (value == NULL) {
        assert(p == NULL);
        goto Done;
    }
    p = (struct key *)malloc(sizeof(struct key));
    if (p != NULL) {
        p->id = id;
        p->key = key;
        p->value = value;
        p->next = keyhead;
        keyhead = p;
    }
 Done:
    PyThread_release_lock(keymutex);
    return p;
}

/* Return a new key.  This must be called before any other functions in
 * this family, and callers must arrange to serialize calls to this
 * function.  No violations are detected.
 */
int
PyThread_create_key(void)
{
    /* All parts of this function are wrong if it's called by multiple
     * threads simultaneously.
     */
    if (keymutex == NULL)
        keymutex = PyThread_allocate_lock();
    return ++nkeys;
}

/* Forget the associations for key across *all* threads. */
void
PyThread_delete_key(int key)
{
    struct key *p, **q;

    PyThread_acquire_lock(keymutex, 1);
    q = &keyhead;
    while ((p = *q) != NULL) {
        if (p->key == key) {
            *q = p->next;
            free((void *)p);
            /* NB This does *not* free p->value! */
        }
        else
            q = &p->next;
    }
    PyThread_release_lock(keymutex);
}

/* Confusing:  If the current thread has an association for key,
 * value is ignored, and 0 is returned.  Else an attempt is made to create
 * an association of key to value for the current thread.  0 is returned
 * if that succeeds, but -1 is returned if there's not enough memory
 * to create the association.  value must not be NULL.
 */
int
PyThread_set_key_value(int key, void *value)
{
    struct key *p;

    assert(value != NULL);
    p = find_key(key, value);
    if (p == NULL)
        return -1;
    else
        return 0;
}

/* Retrieve the value associated with key in the current thread, or NULL
 * if the current thread doesn't have an association for key.
 */
void *
PyThread_get_key_value(int key)
{
    struct key *p = find_key(key, NULL);

    if (p == NULL)
        return NULL;
    else
        return p->value;
}

/* Forget the current thread's association for key, if any. */
void
PyThread_delete_key_value(int key)
{
    long id = PyThread_get_thread_ident();
    struct key *p, **q;

    PyThread_acquire_lock(keymutex, 1);
    q = &keyhead;
    while ((p = *q) != NULL) {
        if (p->key == key && p->id == id) {
            *q = p->next;
            free((void *)p);
            /* NB This does *not* free p->value! */
            break;
        }
        else
            q = &p->next;
    }
    PyThread_release_lock(keymutex);
}

/* Forget everything not associated with the current thread id.
 * This function is called from PyOS_AfterFork().  It is necessary
 * because other thread ids which were in use at the time of the fork
 * may be reused for new threads created in the forked process.
 */
void
PyThread_ReInitTLS(void)
{
    long id = PyThread_get_thread_ident();
    struct key *p, **q;

    if (!keymutex)
        return;

    /* As with interpreter_lock in PyEval_ReInitThreads()
       we just create a new lock without freeing the old one */
    keymutex = PyThread_allocate_lock();

    /* Delete all keys which do not match the current thread id */
    q = &keyhead;
    while ((p = *q) != NULL) {
        if (p->id != id) {
            *q = p->next;
            free((void *)p);
            /* NB This does *not* free p->value! */
        }
        else
            q = &p->next;
    }
}

#endif  /* !MS_WINDOWS */
