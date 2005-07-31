/************************************************************/
/***  C header subsection: math module                    ***/

/* The functions below are mapped to functions from pypy.rpython.module.*
   by the pypy.translator.c.extfunc.EXTERNALS dictionary.
   They should correspond to the functions with the suggested_primitive
   flag set.
*/


/* XXX completely ignoring exceptions/error checking for now */


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

double LL_math_ldexp(double x, long y) {
  return ldexp(x, (int) y);
}

double LL_math_hypot(double x, double y) {
  return hypot(x, y);
}


RPyMODF_RESULT* LL_math_modf(double x) {
  double intpart;
  double fracpart = modf(x, &intpart);
  return ll_modf_result(fracpart, intpart);
}

/* simple math function */

double LL_math_acos(double x) {
    return acos(x);
}

double LL_math_asin(double x) {
    return asin(x);
}

double LL_math_atan(double x) {
    return atan(x);
}

double LL_math_ceil(double x) {
    return ceil(x);
}

double LL_math_cos(double x) {
    return cos(x);
}

double LL_math_cosh(double x) {
    return cosh(x);
}

double LL_math_exp(double x) {
    return exp(x);
}

double LL_math_fabs(double x) {
    return fabs(x);
}

double LL_math_floor(double x) {
    return floor(x);
}

double LL_math_log(double x) {
    return log(x);
}

double LL_math_log10(double x) {
    return log10(x);
}

double LL_math_sin(double x) {
    return sin(x);
}

double LL_math_sinh(double x) {
    return sinh(x);
}

double LL_math_sqrt(double x) {
    return sqrt(x);
}

double LL_math_tan(double x) {
    return tan(x);
}

double LL_math_tanh(double x) {
    return tanh(x);
}
