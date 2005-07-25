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
/* LL_math_frexp XXX strange stuff*/
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

/* LL_math_modf XXXX strange stuff*/

