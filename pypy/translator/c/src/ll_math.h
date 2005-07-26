/************************************************************/
/***  C header subsection: math module                    ***/

#include "math.h"

/* The functions below are mapped to functions from pypy.rpython.module.*
   by the pypy.translator.c.extfunc.EXTERNALS dictionary.
   They should correspond to the functions with the suggested_primitive
   flag set.
*/


/* XXX completely ignoring exceptions/error checking for now */
double LL_math_log10(double x) {
  return log10(x);
}
double LL_math_ceil(double x) {
  return ceil(x);
}

RPyFREXP_RESULT* LL_math_frexp(double x) {
  int expo;
  double m = frexp(x, &expo);
  return ll_frexp_result(m, expo);
}

double LL_math_atan2(double x, double y) {
  return atan2(x, y);
}
double LL_math_fmod(double x, double y) {
  return fmod(x, y);
}
double LL_math_floor(double x) {
  return floor(x);
}
double LL_math_exp(double x) {
  return exp(x);
}
double LL_math_ldexp(double x, long y) {
  return ldexp(x, (int) y);
}

RPyMODF_RESULT* LL_math_modf(double x) {
  double intpart;
  double fracpart = modf(x, &intpart);
  return ll_modf_result(fracpart, intpart);
}

