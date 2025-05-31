// This is a slimmed-down copy of includes/pytime.h. It removes all the
// PyObject interfaces and can be parsed by CTypeSpace

// Do not include it after Python.h
#ifndef Py_PYTHON_H
#include <stdint.h>
#include <limits.h>
#ifdef HAVE_SYS_TIME_H
#include <sys/time.h>
#endif
#include <time.h>
#include <assert.h>
#include <math.h>
#include <errno.h>
#include "src/precommondefs.h"

#define PyAPI_FUNC(x) x
#define PyErr_SetFromErrno(x) 
#define Py_ABS(x) ((x) < 0 ? -(x) : (x))


// Original pytime.h starts here

// The _PyTime_t API is written to use timestamp and timeout values stored in
// various formats and to read clocks.
//
// The _PyTime_t type is an integer to support directly common arithmetic
// operations like t1 + t2.
//
// The _PyTime_t API supports a resolution of 1 nanosecond. The _PyTime_t type
// is signed to support negative timestamps. The supported range is around
// [-292.3 years; +292.3 years]. Using the Unix epoch (January 1st, 1970), the
// supported date range is around [1677-09-21; 2262-04-11].
//
// Formats:
//
// * seconds
// * seconds as a floating pointer number (C double)
// * milliseconds (10^-3 seconds)
// * microseconds (10^-6 seconds)
// * 100 nanoseconds (10^-7 seconds)
// * nanoseconds (10^-9 seconds)
// * timeval structure, 1 microsecond resolution (10^-6 seconds)
// * timespec structure, 1 nanosecond resolution (10^-9 seconds)
//
// Integer overflows are detected and raise OverflowError. Conversion to a
// resolution worse than 1 nanosecond is rounded correctly with the requested
// rounding mode. There are 4 rounding modes: floor (towards -inf), ceiling
// (towards +inf), half even and up (away from zero).
//
// Some functions clamp the result in the range [_PyTime_MIN; _PyTime_MAX], so
// the caller doesn't have to handle errors and doesn't need to hold the GIL.
// For example, _PyTime_Add(t1, t2) computes t1+t2 and clamp the result on
// overflow.
//
// Clocks:
//
// * System clock
// * Monotonic clock
// * Performance counter
//
// Operations like (t * k / q) with integers are implemented in a way to reduce
// the risk of integer overflow. Such operation is used to convert a clock
// value expressed in ticks with a frequency to _PyTime_t, like
// QueryPerformanceCounter() with QueryPerformanceFrequency().

/* _PyTime_t: Python timestamp with subsecond precision. It can be used to
   store a duration, and so indirectly a date (related to another date, like
   UNIX epoch). */
typedef int64_t _PyTime_t;
// _PyTime_MIN nanoseconds is around -292.3 years
#define _PyTime_MIN INT64_MIN
// _PyTime_MAX nanoseconds is around +292.3 years
#define _PyTime_MAX INT64_MAX
#define _SIZEOF_PYTIME_T 8

// parse from here

typedef enum {
    /* Round towards minus infinity (-inf).
       For example, used to read a clock. */
    _PyTime_ROUND_FLOOR=0,
    /* Round towards infinity (+inf).
       For example, used for timeout to wait "at least" N seconds. */
    _PyTime_ROUND_CEILING=1,
    /* Round to nearest with ties going to nearest even integer.
       For example, used to round from a Python float. */
    _PyTime_ROUND_HALF_EVEN=2,
    /* Round away from zero
       For example, used for timeout. _PyTime_ROUND_CEILING rounds
       -1e-9 to 0 milliseconds which causes bpo-31786 issue.
       _PyTime_ROUND_UP rounds -1e-9 to -1 millisecond which keeps
       the timeout sign as expected. select.poll(timeout) must block
       for negative values." */
    _PyTime_ROUND_UP=3,
    /* _PyTime_ROUND_TIMEOUT (an alias for _PyTime_ROUND_UP) should be
       used for timeouts. */
    _PyTime_ROUND_TIMEOUT = _PyTime_ROUND_UP
} _PyTime_round_t;

/* Structure used by time.get_clock_info() */
typedef struct {
    const char *implementation;
    int monotonic;
    int adjustable;
    double resolution;
} _Py_clock_info_t;

// stop parsing

/* Create a timestamp from a number of seconds. */
_PyTime_t _PyTime_FromSeconds(int seconds);

/* Macro to create a timestamp from a number of seconds, no integer overflow.
   Only use the macro for small values, prefer _PyTime_FromSeconds(). */
#define _PYTIME_FROMSECONDS(seconds) \
            ((_PyTime_t)(seconds) * (1000 * 1000 * 1000))

/* Create a timestamp from a number of nanoseconds. */
_PyTime_t _PyTime_FromNanoseconds(_PyTime_t ns);

/* Convert a timestamp to a number of seconds as a C double. */
RPY_EXTERN double
_PyTime_AsSecondsDouble(_PyTime_t t);

/* Convert timestamp to a number of nanoseconds (10^-9 seconds). */
_PyTime_t _PyTime_AsNanoseconds(_PyTime_t t);

// Compute t1 + t2. Clamp to [_PyTime_MIN; _PyTime_MAX] on overflow.
_PyTime_t _PyTime_Add(_PyTime_t t1, _PyTime_t t2);

/* Compute ticks * mul / div.
   Clamp to [_PyTime_MIN; _PyTime_MAX] on overflow.
   The caller must ensure that ((div - 1) * mul) cannot overflow. */
_PyTime_t _PyTime_MulDiv(_PyTime_t ticks,
    _PyTime_t mul,
    _PyTime_t div);

/* Get the current time from the system clock.

   If the internal clock fails, silently ignore the error and return 0.
   On integer overflow, silently ignore the overflow and clamp the clock to
   [_PyTime_MIN; _PyTime_MAX].

   Use _PyTime_GetSystemClockWithInfo() to check for failure. */
_PyTime_t _PyTime_GetSystemClock(void);

/* Get the current time from the system clock.
 * On success, set *t and *info (if not NULL), and return 0.
 * On error, raise an exception and return -1.
 */
RPY_EXTERN int
_PyTime_GetSystemClockWithInfo(_PyTime_t *t, _Py_clock_info_t *info);

/* Get the time of a monotonic clock, i.e. a clock that cannot go backwards.
   The clock is not affected by system clock updates. The reference point of
   the returned value is undefined, so that only the difference between the
   results of consecutive calls is valid.

   If the internal clock fails, silently ignore the error and return 0.
   On integer overflow, silently ignore the overflow and clamp the clock to
   [_PyTime_MIN; _PyTime_MAX].

   Use _PyTime_GetMonotonicClockWithInfo() to check for failure. */
_PyTime_t _PyTime_GetMonotonicClock(void);

/* Get the time of a monotonic clock, i.e. a clock that cannot go backwards.
   The clock is not affected by system clock updates. The reference point of
   the returned value is undefined, so that only the difference between the
   results of consecutive calls is valid.

   Fill info (if set) with information of the function used to get the time.

   Return 0 on success, raise an exception and return -1 on error. */
RPY_EXTERN int
_PyTime_GetMonotonicClockWithInfo(_PyTime_t *t, _Py_clock_info_t *info);

/* Get the performance counter: clock with the highest available resolution to
   measure a short duration.

   If the internal clock fails, silently ignore the error and return 0.
   On integer overflow, silently ignore the overflow and clamp the clock to
   [_PyTime_MIN; _PyTime_MAX].

   Use _PyTime_GetPerfCounterWithInfo() to check for failure. */
_PyTime_t _PyTime_GetPerfCounter(void);

/* Get the performance counter: clock with the highest available resolution to
   measure a short duration.

   Fill info (if set) with information of the function used to get the time.

   Return 0 on success, raise an exception and return -1 on error. */
RPY_EXTERN int
_PyTime_GetPerfCounterWithInfo(_PyTime_t *t, _Py_clock_info_t *info);


// Create a deadline.
// Pseudo code: _PyTime_GetMonotonicClock() + timeout.
_PyTime_t _PyDeadline_Init(_PyTime_t timeout);

// Get remaining time from a deadline.
// Pseudo code: deadline - _PyTime_GetMonotonicClock().
_PyTime_t _PyDeadline_Get(_PyTime_t deadline);

RPY_EXTERN int
_PyTime_AsTimeval(_PyTime_t t, struct timeval *tv, _PyTime_round_t round);

RPY_EXTERN int
_PyTime_AsTimespec(_PyTime_t t, struct timespec *ts);

#endif
