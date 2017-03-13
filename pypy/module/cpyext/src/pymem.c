#include <Python.h>

void *
PyMem_RawMalloc(size_t size)
{
    /*
     * Limit ourselves to PY_SSIZE_T_MAX bytes to prevent security holes.
     * Most python internals blindly use a signed Py_ssize_t to track
     * things without checking for overflows or negatives.
     * As size_t is unsigned, checking for size < 0 is not required.
     */
    if (size > (size_t)PY_SSIZE_T_MAX)
        return NULL;
    if (size == 0)
        size = 1;
    return malloc(size);
}

void *
PyMem_RawCalloc(size_t nelem, size_t elsize)
{
    /* see PyMem_RawMalloc() */
    if (elsize != 0 && nelem > (size_t)PY_SSIZE_T_MAX / elsize)
        return NULL;
    /* PyMem_RawCalloc(0, 0) means calloc(1, 1). Some systems would return NULL
       for calloc(0, 0), which would be treated as an error. Some platforms
       would return a pointer with no memory behind it, which would break
       pymalloc.  To solve these problems, allocate an extra byte. */
    if (nelem == 0 || elsize == 0) {
        nelem = 1;
        elsize = 1;
    }
    return calloc(nelem, elsize);
}

void*
PyMem_RawRealloc(void *ptr, size_t size)
{
    /* see PyMem_RawMalloc() */
    if (size > (size_t)PY_SSIZE_T_MAX)
        return NULL;
    if (size == 0)
        size = 1;
    return realloc(ptr, size);
}

void PyMem_RawFree(void *ptr)
{
    free(ptr);
}


/* the PyMem_Xxx functions are the same as PyMem_RawXxx in PyPy, for now */
void *PyMem_Malloc(size_t size)
{
    if (size > (size_t)PY_SSIZE_T_MAX)
        return NULL;
    if (size == 0)
        size = 1;
    return malloc(size);
}

void *PyMem_Calloc(size_t nelem, size_t elsize)
{
    if (elsize != 0 && nelem > (size_t)PY_SSIZE_T_MAX / elsize)
        return NULL;
    if (nelem == 0 || elsize == 0) {
        nelem = 1;
        elsize = 1;
    }
    return calloc(nelem, elsize);
}

void* PyMem_Realloc(void *ptr, size_t size)
{
    if (size > (size_t)PY_SSIZE_T_MAX)
        return NULL;
    if (size == 0)
        size = 1;
    return realloc(ptr, size);
}

void PyMem_Free(void *ptr)
{
    free(ptr);
}

int _PyTraceMalloc_Track(_PyTraceMalloc_domain_t domain,
                         uintptr_t ptr, size_t size)
{
    /* to avoid acquiring/releasing the GIL too often, only do it
       if the total reported size exceeds 64KB. */
    static volatile long unreported_size = 0;
    long prev, next, report;

    size += sizeof(long);
    /* ^^^ to account for some alignment.  Important, otherwise we'd
     * collect sizes of, say, 1-bytes mallocs in 1-bytes increment */

 retry:
    report = 0;
    prev = unreported_size;
    next = prev + size;
    if (next >= 65536) {
        report = next;
        next = 0;
    }
    if (prev != next) {
#ifdef _WIN32
        if (InterlockedCompareExchange(&unreported_size, next, prev) != prev)
            goto retry;
#else
        if (!__sync_bool_compare_and_swap(&unreported_size, prev, next))
            goto retry;
#endif
    }

    if (report) {
        PyGILState_STATE state = PyGILState_Ensure();
        _PyPyGC_AddMemoryPressure(report);
        PyGILState_Release(state);
    }
}

int _PyTraceMalloc_Untrack(_PyTraceMalloc_domain_t domain,
                           uintptr_t ptr)
{
    /* nothing */
}
