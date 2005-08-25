#include <errno.h>
#include <python2.3/Python.h>

#define NULL (void *) 0

#define LL_MATH_SET_ERANGE_IF_MATH_ERROR Py_SET_ERANGE_IF_OVERFLOW

// c forward declarations
double frexp(double, int*);

struct RPyFREXP_RESULT;
struct RPyMODF_RESULT;

struct RPyFREXP_RESULT *ll_frexp_result__Float_Signed(double, int);
struct RPyMODF_RESULT *ll_frexp_result__Float_Float(double, double);

void prepare_and_raise_OverflowError(char *);
void prepare_and_raise_ValueError(char *);

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
	return ll_modf_result(fracpart, intpart);
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
