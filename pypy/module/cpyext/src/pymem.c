#include <Python.h>

void * PyMem_Malloc(size_t n)
{
    return malloc((n) ? (n) : 1);
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
