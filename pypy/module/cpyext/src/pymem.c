#ifdef _WIN32
#  define _WIN32_WINNT 0x0501
#endif

#include <Python.h>

#ifdef _WIN32
#  include <Windows.h>
#endif


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

    /* Should we return -2 or 0?  In theory it should be -2, because
       we're not using the info to really track the allocations.
       But I'm sure someone is too clever somewhere and stops calling
       _PyTraceMalloc_Track() if it returns -2.  On the other hand,
       returning 0 might lead to expectations that importing
       'tracemalloc' works on Python 3.  Oh well, in that case we'll
       just crash with ImportError during 'import tracemalloc'.
     */
    return 0;
}

int _PyTraceMalloc_Untrack(_PyTraceMalloc_domain_t domain,
                           uintptr_t ptr)
{
    /* nothing to do */
    return 0;
}
