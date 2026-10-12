#include "compat.h"

#include <string.h>
#include <assert.h>
#if VMPROF_WINDOWS
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#else
#include <time.h>
#include <sys/time.h>
#endif

static int _vmp_profile_fileno = -1;

int vmp_profile_fileno(void) {
    return _vmp_profile_fileno;
}
void vmp_set_profile_fileno(int fileno) {
    _vmp_profile_fileno = fileno;
}

#ifndef VMPROF_WINDOWS
int vmp_write_all(const char *buf, size_t bufsize)
{
    ssize_t count;
    if (_vmp_profile_fileno == -1) {
        return -1;
    }
    while (bufsize > 0) {
        count = write(_vmp_profile_fileno, buf, bufsize);
        if (count <= 0)
            return -1;   /* failed */
        buf += count;
        bufsize -= count;
    }
    return 0;
}
#endif

int vmp_write_meta(const char * key, const char * value)
{
    char marker = MARKER_META;
    long x = (long)strlen(key);
    vmp_write_all(&marker, 1);
    vmp_write_all((char*)&x, sizeof(long));
    vmp_write_all(key, x);
    x = (long)strlen(value);
    vmp_write_all((char*)&x, sizeof(long));
    vmp_write_all(value, x);
    return 0;
}

/**
 * Write the time and zone now.
 */

struct timezone_buf {
    int64_t tv_sec;
    int64_t tv_usec;
};
#define __SIZE (1+sizeof(struct timezone_buf)+8)

#ifdef VMPROF_UNIX
int vmp_write_time_now(int marker) {
    char buffer[__SIZE];
    struct timezone_buf buf;

    (void)memset(&buffer, 0, __SIZE);

    assert((marker == MARKER_TRAILER || marker == MARKER_TIME_N_ZONE) && \
           "marker must be either a trailer or time_n_zone!");

    struct timeval tv;
    time_t now;
    struct tm tm;


    /* copy over to the struct */
    if (gettimeofday(&tv, NULL) != 0) {
        return -1;
    }
    if (time(&now) == (time_t)-1) {
        return -1;
    }
    if (localtime_r(&now, &tm) == NULL) {
        return -1;
    }
    buf.tv_sec = tv.tv_sec;
    buf.tv_usec = tv.tv_usec;
    // IF we really support time zones:
    // use a cross platform datetime library that outputs iso8601 strings
    // strncpy(((char*)buffer)+__SIZE-8, tm.tm_zone, 8);

    buffer[0] = marker;
    (void)memcpy(buffer+1, &buf, sizeof(struct timezone_buf));
    vmp_write_all(buffer, __SIZE);
    return 0;
}

#if defined(VMPROF_APPLE) && !defined(CLOCK_MONOTONIC)
/* SDK older than macOS 10.12: no clock_gettime.  mach_absolute_time is a
   monotonic clock; there is no signal-safe process cpu clock, so both
   modes use it (it is what setitimer(ITIMER_REAL) measures anyway). */
#include <mach/mach_time.h>
int64_t vmp_sample_time_ns(int cpu_time)
{
    mach_timebase_info_data_t tb;
    uint64_t t = mach_absolute_time();
    (void)cpu_time;
    if (mach_timebase_info(&tb) != KERN_SUCCESS || tb.denom == 0)
        return (int64_t)t;
    return (int64_t)(t / tb.denom * tb.numer + t % tb.denom * tb.numer / tb.denom);
}
#else
int64_t vmp_sample_time_ns(int cpu_time)
{
    struct timespec ts;
    clockid_t clk = cpu_time ? CLOCK_PROCESS_CPUTIME_ID : CLOCK_MONOTONIC;
    if (clock_gettime(clk, &ts) != 0)
        return 0;
    return (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}
#endif
#endif

#ifdef VMPROF_WINDOWS
int64_t vmp_sample_time_ns(int cpu_time)
{
    /* the frequency is fixed at boot, so it is safe to cache it */
    static LARGE_INTEGER freq;
    LARGE_INTEGER now;
    (void)cpu_time;
    if (freq.QuadPart == 0 && !QueryPerformanceFrequency(&freq))
        return 0;
    if (!QueryPerformanceCounter(&now))
        return 0;
    return (int64_t)(now.QuadPart / freq.QuadPart * 1000000000LL +
                     now.QuadPart % freq.QuadPart * 1000000000LL / freq.QuadPart);
}

int vmp_write_time_now(int marker) {
    char buffer[__SIZE];
    struct timezone_buf buf;

    /**
     * http://stackoverflow.com/questions/10905892/equivalent-of-gettimeday-for-windows
     */

    // Note: some broken versions only have 8 trailing zero's, the correct
    // epoch has 9 trailing zero's
    static const uint64_t EPOCH = ((uint64_t) 116444736000000000ULL);

    SYSTEMTIME  system_time;
    FILETIME    file_time;
    uint64_t    time;

    (void)memset(&buffer, 0, __SIZE);

    assert((marker == MARKER_TRAILER || marker == MARKER_TIME_N_ZONE) && \
           "marker must be either a trailer or time_n_zone!");


    GetSystemTime( &system_time );
    SystemTimeToFileTime( &system_time, &file_time );
    time =  ((uint64_t)file_time.dwLowDateTime )      ;
    time += ((uint64_t)file_time.dwHighDateTime) << 32;

    buf.tv_sec = ((time - EPOCH) / 10000000L);
    buf.tv_usec = (system_time.wMilliseconds * 1000);

    // time zone not implemented on windows
    // IF we really support time zones:
    // use a cross platform datetime library that outputs iso8601 strings
    memset(((char*)buffer)+__SIZE-8, 0, 8);

    buffer[0] = marker;
    (void)memcpy(buffer+1, &buf, sizeof(struct timezone_buf));
    vmp_write_all(buffer, __SIZE);
    return 0;
}
#endif
#undef __SIZE
