/************************************************************/
/***  C header subsection: math module                    ***/

/* The functions below are mapped to functions from pypy.rpython.module.*
   by the pypy.translator.c.extfunc.EXTERNALS dictionary.
   They should correspond to the functions with the suggested_primitive
   flag set.
*/

/* xxx macro from pyport.h, at some point define our owns */
/* xxx this 2.3 name is later deprecated  */
#include <errno.h>
#define LL_MATH_SET_ERANGE_IF_MATH_ERROR Py_SET_ERANGE_IF_OVERFLOW

#define LL_MATH_ERROR_RESET errno = 0

#define LL_MATH_CHECK_ERROR(x, errret) do {  \
	LL_MATH_SET_ERANGE_IF_MATH_ERROR(x); \
	if (errno && ll_math_is_error(x))    \
		return errret;               \
} while(0)


/* prototypes */

int ll_math_is_error(double x);
double LL_math_pow(double x, double y);
double LL_math_atan2(double x, double y);
double LL_math_fmod(double x, double y);
double LL_math_ldexp(double x, long y);
double LL_math_hypot(double x, double y);
double LL_math_acos(double x);
double LL_math_asin(double x);
double LL_math_atan(double x);
double LL_math_ceil(double x);
double LL_math_cos(double x);
double LL_math_cosh(double x);
double LL_math_exp(double x);
double LL_math_fabs(double x);
double LL_math_floor(double x);
double LL_math_log(double x);
double LL_math_log10(double x);
double LL_math_sin(double x);
double LL_math_sinh(double x);
double LL_math_sqrt(double x);
double LL_math_tan(double x);
double LL_math_tanh(double x);


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

int ll_math_is_error(double x) {
	if (errno == ERANGE) {
		if (!x) 
			return 0;
		RPyRaiseSimpleException(PyExc_OverflowError, "math range error");
	} else {
		RPyRaiseSimpleException(PyExc_ValueError, "math domain error");
	}
	return 1;
}

double LL_math_pow(double x, double y) {
	double r;
	LL_MATH_ERROR_RESET;
	r = pow(x, y);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_atan2(double x, double y) {
	double r;
	LL_MATH_ERROR_RESET;
	r = atan2(x, y);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_fmod(double x, double y) {
	double r;
	LL_MATH_ERROR_RESET;
	r = fmod(x, y);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_ldexp(double x, long y) {
	double r;
	LL_MATH_ERROR_RESET;
	r = ldexp(x, (int) y);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_hypot(double x, double y) {
	double r;
	LL_MATH_ERROR_RESET;
	r = hypot(x, y);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}


/* simple math function */

double LL_math_acos(double x) {
	double r;	
	LL_MATH_ERROR_RESET;
	r = acos(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_asin(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = asin(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_atan(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = atan(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_ceil(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = ceil(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_cos(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = cos(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_cosh(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = cosh(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_exp(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = exp(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_fabs(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = fabs(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_floor(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = floor(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_log(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = log(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_log10(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = log10(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_sin(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = sin(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_sinh(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = sinh(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_sqrt(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = sqrt(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_tan(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = tan(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

double LL_math_tanh(double x) {
	double r;
	LL_MATH_ERROR_RESET;
	r = tanh(x);
	LL_MATH_CHECK_ERROR(r, -1.0);
	return r;
}

#endif /* PYPY_NOT_MAIN_FILE */
