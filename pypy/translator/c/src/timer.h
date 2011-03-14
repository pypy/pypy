#ifndef PYPY_TIMER_H
#define PYPY_TIMER_H

/* XXX Some overlap with the stuff in debug_print
 */
#define OP_LL_READ_TIMESTAMP(v) v = pypy_read_timestamp();

#ifndef PYPY_NOT_MAIN_FILE
/* implementations */

#ifdef _WIN32
long long pypy_read_timestamp(void) {
    long long timestamp;
    long long scale;
    QueryPerformanceCounter((LARGE_INTEGER*)&(timestamp));
    return timestamp;
}

#else

#include "inttypes.h"

long long pypy_read_timestamp(void) {
    uint32_t low, high;
    __asm__ __volatile__ (
        "rdtsc" : "=a" (low), "=d" (high)
    );
    return ((long long)high << 32) + low;
}

#endif
#endif
#endif
