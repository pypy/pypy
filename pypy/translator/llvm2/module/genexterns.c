#include <errno.h>
#include <python2.3/Python.h>

#define NULL (void *) 0

#define LL_MATH_SET_ERANGE_IF_MATH_ERROR Py_SET_ERANGE_IF_OVERFLOW

struct RPyFREXP_RESULT;
struct RPyFREXP_RESULT *ll_frexp_result__Float_Signed(double, int);

void prepare_and_raise_ValueError(char *);
void prepare_and_raise_OverflowError(char *);

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


struct RPyFREXP_RESULT* ll_math_frexp(double x) {
	int expo;
	double m;
	LL_MATH_ERROR_RESET;
	m= frexp(x, &expo);
	LL_MATH_CHECK_ERROR(m, NULL);
	return ll_frexp_result__Float_Signed(m, expo);
}
