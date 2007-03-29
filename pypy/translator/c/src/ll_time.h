/************************************************************/
 /***  C header subsection: time module                    ***/

#include <time.h>
#ifndef MS_WINDOWS
#  include <sys/time.h>
#endif


/* prototypes */

double LL_time_clock(void);
void LL_time_sleep(double secs);
double LL_time_time(void);


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

/****** clock() ******/

#if defined(MS_WINDOWS) && !defined(MS_WIN64) && !defined(__BORLANDC__)
/* Win32 has better clock replacement
   XXX Win64 does not yet, but might when the platform matures. */
#include <windows.h>


double LL_time_clock(void)
{
	static LARGE_INTEGER ctrStart;
	static double divisor = 0.0;
	LARGE_INTEGER now;
	double diff;

	if (divisor == 0.0) {
		LARGE_INTEGER freq;
		QueryPerformanceCounter(&ctrStart);
		if (!QueryPerformanceFrequency(&freq) || freq.QuadPart == 0) {
			/* Unlikely to happen - this works on all intel
			   machines at least!  Revert to clock() */
			return ((double)clock()) / CLOCKS_PER_SEC;
		}
		divisor = (double)freq.QuadPart;
	}
	QueryPerformanceCounter(&now);
	diff = (double)(now.QuadPart - ctrStart.QuadPart);
	return diff / divisor;
}

#else  /* if !MS_WINDOWS */

#ifndef CLOCKS_PER_SEC
#ifdef CLK_TCK
#define CLOCKS_PER_SEC CLK_TCK
#else
#define CLOCKS_PER_SEC 1000000
#endif
#endif

double LL_time_clock(void)
{
	return ((double)clock()) / CLOCKS_PER_SEC;
}
#endif /* MS_WINDOWS */


void LL_time_sleep(double secs)
{
#if defined(MS_WINDOWS)
	double millisecs = secs * 1000.0;
	unsigned long ul_millis;

	if (millisecs > (double)ULONG_MAX) {
		RPyRaiseSimpleException(PyExc_OverflowError,
				     "sleep length is too large");
		return;
	}
	ul_millis = (unsigned long)millisecs;
        /* XXX copy CPython to make this interruptible again */
	/*if (ul_millis == 0)*/
		Sleep(ul_millis);
	/*else {
		DWORD rc;
		ResetEvent(hInterruptEvent);
		rc = WaitForSingleObject(hInterruptEvent, ul_millis);
		if (rc == WAIT_OBJECT_0) {
				 * Yield to make sure real Python signal
				 * handler called.
				 *
			Sleep(1);
			RPyRaiseSimpleException(PyExc_IOError, "interrupted");
			return;
		}
	}*/
#else
	struct timeval t;
	double frac;
	frac = fmod(secs, 1.0);
	secs = floor(secs);
	t.tv_sec = (long)secs;
	t.tv_usec = (long)(frac*1000000.0);
	if (select(0, (fd_set *)0, (fd_set *)0, (fd_set *)0, &t) != 0) {
#ifdef EINTR
		if (errno != EINTR) {
#else
		if (1) {
#endif
			RPyRaiseSimpleException(PyExc_IOError, "select() failed");
			return;
		}
	}
#endif
}


#ifdef HAVE_FTIME
#include <sys/timeb.h>
#if !defined(MS_WINDOWS) && !defined(PYOS_OS2)
extern int ftime(struct timeb *);
#endif /* MS_WINDOWS */
#endif /* HAVE_FTIME */

static double
ll_floattime(void)
{
	/* There are three ways to get the time:
	  (1) gettimeofday() -- resolution in microseconds
	  (2) ftime() -- resolution in milliseconds
	  (3) time() -- resolution in seconds
	  In all cases the return value is a float in seconds.
	  Since on some systems (e.g. SCO ODT 3.0) gettimeofday() may
	  fail, so we fall back on ftime() or time().
	  Note: clock resolution does not imply clock accuracy! */
#ifdef HAVE_GETTIMEOFDAY
	{
		struct timeval t;
#ifdef GETTIMEOFDAY_NO_TZ
		if (gettimeofday(&t) == 0)
			return (double)t.tv_sec + t.tv_usec*0.000001;
#else /* !GETTIMEOFDAY_NO_TZ */
		if (gettimeofday(&t, (struct timezone *)NULL) == 0)
			return (double)t.tv_sec + t.tv_usec*0.000001;
#endif /* !GETTIMEOFDAY_NO_TZ */
	}
#endif /* !HAVE_GETTIMEOFDAY */
	{
#if defined(HAVE_FTIME)
		struct timeb t;
		ftime(&t);
		return (double)t.time + (double)t.millitm * (double)0.001;
#else /* !HAVE_FTIME */
		time_t secs;
		time(&secs);
		return (double)secs;
#endif /* !HAVE_FTIME */
	}
}

double LL_time_time(void) /* xxx had support for better resolutions */
{
	return ll_floattime();
}

#endif /* PYPY_NOT_MAIN_FILE */
