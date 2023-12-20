/* Internal header for all the files in hpy/trace/src. The public API is in
   include/hpy_trace.h
*/
#ifndef HPY_TRACE_INTERNAL_H
#define HPY_TRACE_INTERNAL_H

#include <assert.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif
#include "hpy.h"
#include "hpy_trace.h"


#define HPY_TRACE_MAGIC 0xF00BAA5

// frequency of nanosecond resolution
#define FREQ_NSEC 1000000000L

/* === HPyTraceInfo === */

#ifdef _WIN32
typedef LARGE_INTEGER _HPyTime_t;
typedef BOOL _HPyClockStatus_t;
#else
typedef struct timespec _HPyTime_t;
typedef int _HPyClockStatus_t;
#endif

typedef struct {
    long magic_number; // used just for sanity checks
    HPyContext *uctx;
    /* frequency of the used performance counter */
    _HPyTime_t counter_freq;
#ifdef _WIN32
    /* to_ns = FREQ_NS / counter_freq  */
    int64_t to_ns;
#endif
    /* call count of the corresponding HPy API function */
    uint64_t *call_counts;
    /* durations spent in the corresponding HPy API function */
    _HPyTime_t *durations;
    HPy on_enter_func;
    HPy on_exit_func;
} HPyTraceInfo;


static inline HPyTraceInfo *get_info(HPyContext *tctx)
{
    HPyTraceInfo *info = (HPyTraceInfo*)tctx->_private;
    assert(info->magic_number == HPY_TRACE_MAGIC); // sanity check
    return info;
}

/* Get the current value of the monotonic clock.  This is a platform-dependent
   operation. */
static inline _HPyClockStatus_t get_monotonic_clock(_HPyTime_t *t)
{
#ifdef _WIN32
    return (int)QueryPerformanceCounter(t);
#else
    return clock_gettime(CLOCK_MONOTONIC_RAW, t);
#endif
}

HPyTraceInfo *hpy_trace_on_enter(HPyContext *tctx, int id);
void hpy_trace_on_exit(HPyTraceInfo *info, int id, _HPyClockStatus_t r0,
        _HPyClockStatus_t r1, _HPyTime_t *_ts_start, _HPyTime_t *_ts_end);

#endif /* HPY_TRACE_INTERNAL_H */
