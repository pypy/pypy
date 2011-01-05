#ifndef PYPY_TIMER_H
#define PYPY_TIMER_H

/* XXX Some overlap with the stuff in debug_print
 */

/* prototypes */
double pypy_read_timestamp_double(void);

#ifndef PYPY_NOT_MAIN_FILE
/* implementations */

#  ifdef _WIN32
    double pypy_read_timestamp_double(void) {
        static double pypy_timer_scale = 0.0;
        long long timestamp;
        long long scale;
        QueryPerformanceCounter((LARGE_INTEGER*)&(timestamp));
        if (pypy_timer_scale == 0.0) {
          QueryPerformanceFrequency((LARGE_INTEGER*)&(scale));
          pypy_timer_scale = 1.0 / (double)scale;
        }
        return ((double)timestamp) * pypy_timer_scale;
    }

#  else
#    include <time.h>
#    include <sys/time.h>

     double pypy_read_timestamp_double(void)
     {
#    ifdef CLOCK_THREAD_CPUTIME_ID
       struct timespec tspec;
       clock_gettime(CLOCK_THREAD_CPUTIME_ID, &tspec);
       return ((double)tspec.tv_sec) + ((double)tspec.tv_nsec) / 1e9;
#    else
       /* argh, we don't seem to have clock_gettime().  Bad OS. */
       struct timeval tv;
       gettimeofday(&tv, NULL);
       return ((double)tv.tv_sec) + ((double)tv.tv_usec) / 1e6;
#    endif
     }

# endif
#endif
#endif
