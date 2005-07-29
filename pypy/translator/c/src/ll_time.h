/************************************************************/
 /***  C header subsection: time module                    ***/

#include <sys/time.h>
#include <time.h>


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
			return clock();
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
		RaiseSimpleException(Exc_OverflowError,
				     "sleep length is too large");
		return;
	}
	ul_millis = (unsigned long)millisecs;
	if (ul_millis == 0)
		Sleep(ul_millis);
	else {
		DWORD rc;
		ResetEvent(hInterruptEvent);
		rc = WaitForSingleObject(hInterruptEvent, ul_millis);
		if (rc == WAIT_OBJECT_0) {
				/* Yield to make sure real Python signal
				 * handler called.
				 */
			Sleep(1);
			RaiseSimpleException(Exc_IOError, "interrupted");
			return;
		}
	}
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
			RaiseSimpleException(Exc_IOError, "select() failed");
			return;
		}
	}
#endif
}


static double
ll_floattime(void)
{
	time_t secs;
	time(&secs);
	return (double)secs;
}

double LL_time_time(void) /* xxx had support for better resolutions */
{
	return ll_floattime();
}
