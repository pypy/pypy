#include <errno.h>
#include <locale.h>
#include <ctype.h>
#include <python2.3/Python.h>

#define NULL (void *) 0

#define LL_MATH_SET_ERANGE_IF_MATH_ERROR Py_SET_ERANGE_IF_OVERFLOW

// c forward declarations
double frexp(double, int*);

struct RPyFREXP_RESULT;
struct RPyMODF_RESULT;
struct RPyString;

struct RPyFREXP_RESULT *ll_frexp_result__Float_Signed(double, int);
struct RPyMODF_RESULT *ll_modf_result__Float_Float(double, double);

char *RPyString_AsString(struct RPyString*);
int RPyString_Size(struct RPyString_Size*);
struct RPyString *RPyString_FromString(char *);

void prepare_and_raise_OverflowError(char *);
void prepare_and_raise_ValueError(char *);
void prepare_and_raise_IOError(char *);

int ll_math_is_error(double x) {
	if (errno == ERANGE) {
		if (!x) 
			return 0;
		prepare_and_raise_OverflowError("math range error");
	} else {
		prepare_and_raise_ValueError("math domain error");
	}
	return 1;
}

#define LL_MATH_ERROR_RESET errno = 0

#define LL_MATH_CHECK_ERROR(x, errret) do {  \
	LL_MATH_SET_ERANGE_IF_MATH_ERROR(x); \
	if (errno && ll_math_is_error(x))    \
		return errret;               \
} while(0)


double ll_math_pow(double x, double y) {
	double r;
	LL_MATH_ERROR_RESET;
	r = pow(x, y);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_atan2(double x, double y) {
	double r;
	LL_MATH_ERROR_RESET;
	r = atan2(x, y);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_fmod(double x, double y) {
	double r;
	LL_MATH_ERROR_RESET;
	r = fmod(x, y);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_ldexp(double x, long y) {
	double r;
	LL_MATH_ERROR_RESET;
	r = ldexp(x, (int) y);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_hypot(double x, double y) {
	double r;
	LL_MATH_ERROR_RESET;
	r = hypot(x, y);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

struct RPyMODF_RESULT* ll_math_modf(double x) {
	double intpart, fracpart;
	LL_MATH_ERROR_RESET;
	fracpart = modf(x, &intpart);
	LL_MATH_CHECK_ERROR(fracpart, NULL);
	return ll_modf_result__Float_Float(fracpart, intpart);
}

/* simple math function */

double ll_math_acos(double x) {
	double r;	
	LL_MATH_ERROR_RESET;
	r = acos(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_asin(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = asin(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_atan(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = atan(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_ceil(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = ceil(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_cos(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = cos(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_cosh(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = cosh(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_exp(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = exp(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_fabs(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = fabs(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_floor(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = floor(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_log(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = log(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_log10(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = log10(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_sin(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = sin(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_sinh(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = sinh(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_sqrt(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = sqrt(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_tan(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = tan(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double ll_math_tanh(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = tanh(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

struct RPyFREXP_RESULT* ll_math_frexp(double x) {
	int expo;
	double m;
	LL_MATH_ERROR_RESET;
	m= frexp(x, &expo);
	LL_MATH_CHECK_ERROR(m, NULL);
	return ll_frexp_result__Float_Signed(m, expo);
}

/************************************************************/
 /***  C header subsection: time module                    ***/

#include <time.h>
#ifndef MS_WINDOWS
#  include <sys/time.h>
#endif


/****** clock() ******/

#if defined(MS_WINDOWS) && !defined(MS_WIN64) && !defined(__BORLANDC__)
/* Win32 has better clock replacement
   XXX Win64 does not yet, but might when the platform matures. */
#include <windows.h>

double ll_time_clock(void)
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

double ll_time_clock(void)
{
	return ((double)clock()) / CLOCKS_PER_SEC;
}
#endif /* MS_WINDOWS */


void ll_time_sleep(double secs)
{
#if defined(MS_WINDOWS)
	double millisecs = secs * 1000.0;
	unsigned long ul_millis;

	if (millisecs > (double)ULONG_MAX) {
		prepare_and_raise_OverflowError("sleep length is too large");
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
		  prepare_and_raise_IOError("select() failed");
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

double ll_time_time(void) /* xxx had support for better resolutions */
{
	return ll_floattime();
}

double ll_strtod_parts_to_float(struct RPyString *sign, 
				struct RPyString *beforept, 
				struct RPyString *afterpt, 
				struct RPyString *exponent)
{
	char *fail_pos;
	struct lconv *locale_data;
	const char *decimal_point;
	int decimal_point_len;
	double x;
	char *last;
	char *expo = RPyString_AsString(exponent);
	int buf_size;
	char *s;

	if (*expo == '\0') {
		expo = "0";
	}

	locale_data = localeconv();
	decimal_point = locale_data->decimal_point;
	decimal_point_len = strlen(decimal_point);

	buf_size = RPyString_Size(sign) + 
	  RPyString_Size(beforept) +
	  decimal_point_len +
	  RPyString_Size(afterpt) +
	  1 /* e */ +
	  strlen(expo) + 
	  1 /*  asciiz  */ ;

        s = malloc(buf_size);

	strcpy(s, RPyString_AsString(sign));
	strcat(s, RPyString_AsString(beforept));
	strcat(s, decimal_point);
	strcat(s, RPyString_AsString(afterpt));
	strcat(s, "e");
	strcat(s, expo);

	last = s + (buf_size-1);
	x = strtod(s, &fail_pos);
	errno = 0;
	free(s);
	if (fail_pos > last)
		fail_pos = last;
	if (fail_pos == s || *fail_pos != '\0' || fail_pos != last) {
		prepare_and_raise_ValueError("invalid float literal");
		return -1.0;
	}
	if (x == 0.0) { /* maybe a denormal value, ask for atof behavior */
		x = strtod(s, NULL);
		errno = 0;
	}
	return x;
}


struct RPyString *ll_strtod_formatd(struct RPyString *fmt, double x) {
	char buffer[120]; /* this should be enough, from PyString_Format code */
	int buflen = 120;
	int res;
	res = snprintf(buffer, buflen, RPyString_AsString(fmt), x);
	if (res <= 0 || res >= buflen) {
		strcpy(buffer, "??.?"); /* should not occur */
	} else {
		struct lconv *locale_data;
		const char *decimal_point;
		int decimal_point_len;
		char *p;

		locale_data = localeconv();
		decimal_point = locale_data->decimal_point;
		decimal_point_len = strlen(decimal_point);

		if (decimal_point[0] != '.' || 
		    decimal_point[1] != 0)
		{
			p = buffer;

			if (*p == '+' || *p == '-')
				p++;

			while (isdigit((unsigned char)*p))
				p++;

			if (strncmp(p, decimal_point, decimal_point_len) == 0)
			{
				*p = '.';
				p++;
				if (decimal_point_len > 1) {
					int rest_len;
					rest_len = strlen(p + (decimal_point_len - 1));
					memmove(p, p + (decimal_point_len - 1), 
						rest_len);
					p[rest_len] = 0;
				}
			}
		}
		
	}

	return RPyString_FromString(buffer);
}

