#ifndef Py_PYMATH_H
#define Py_PYMATH_H

/**************************************************************************
Symbols and macros to supply platform-independent interfaces to mathematical
functions and constants
**************************************************************************/

/* High precision definition of pi and e (Euler)
 * The values are taken from libc6's math.h.
 */
#ifndef Py_MATH_PIl
#define Py_MATH_PIl 3.1415926535897932384626433832795029L
#endif
#ifndef Py_MATH_PI
#define Py_MATH_PI 3.14159265358979323846
#endif

#ifndef Py_MATH_El
#define Py_MATH_El 2.7182818284590452353602874713526625L
#endif

#ifndef Py_MATH_E
#define Py_MATH_E 2.7182818284590452354
#endif

/* Tau (2pi) to 40 digits, taken from tauday.com/tau-digits. */
#ifndef Py_MATH_TAU
#define Py_MATH_TAU 6.2831853071795864769252867665590057683943L
#endif

/* Py_IS_NAN(X)
 * Return 1 if float or double arg is a NaN, else 0.
 * Caution:
 *     X is evaluated more than once.
 *     This may not work on all platforms.  Each platform has *some*
 *     way to spell this, though -- override in pyconfig.h if you have
 *     a platform where it doesn't work.
 */
#ifndef Py_IS_NAN
#if __STDC_VERSION__ >= 199901L || __cplusplus >= 201103L
#define Py_IS_NAN(X) isnan(X)
#else
#define Py_IS_NAN(X) ((X) != (X))
#endif
#endif

/* Py_IS_INFINITY(X)
 * Return 1 if float or double arg is an infinity, else 0.
 * Caution:
 *    X is evaluated more than once.
 *    This implementation may set the underflow flag if |X| is very small;
 *    it really can't be implemented correctly (& easily) before C99.
 *    Override in pyconfig.h if you have a better spelling on your platform.
 */
#ifndef Py_IS_INFINITY
#  if __STDC_VERSION__ >= 199901L || __cplusplus >= 201103L
#    define Py_IS_INFINITY(X) isinf(X)
#  else
#    define Py_IS_INFINITY(X) ((X) && ((X)*0.5 == (X)))
#  endif
#endif

/* Py_IS_FINITE(X)
 * Return 1 if float or double arg is neither infinite nor NAN, else 0.
 * Some compilers (e.g. VisualStudio) have intrinsics for this, so a special
 * macro for this particular test is useful
 */
#ifndef Py_IS_FINITE
#if __STDC_VERSION__ >= 199901L || __cplusplus >= 201103L
#define Py_IS_FINITE(X) isfinite(X)
#else
#define Py_IS_FINITE(X) (!Py_IS_INFINITY(X) && !Py_IS_NAN(X))
#endif
#endif

/* HUGE_VAL is supposed to expand to a positive double infinity.  Python
 * uses Py_HUGE_VAL instead because some platforms are broken in this
 * respect.  We used to embed code in pyport.h to try to worm around that,
 * but different platforms are broken in conflicting ways.  If you're on
 * a platform where HUGE_VAL is defined incorrectly, fiddle your Python
 * config to #define Py_HUGE_VAL to something that works on your platform.
 */
#ifndef Py_HUGE_VAL
#define Py_HUGE_VAL HUGE_VAL
#endif

/* Py_NAN: Value that evaluates to a quiet Not-a-Number (NaN).  The sign is
 * undefined and normally not relevant, but e.g. fixed for float("nan").
 */
#if !defined(Py_NAN)
#    define Py_NAN ((double)NAN)
#endif
/* Return whether integral type *type* is signed or not. */
#define _Py_IntegralTypeSigned(type) ((type)(-1) < 0)
/* Return the maximum value of integral type *type*. */
#define _Py_IntegralTypeMax(type) ((_Py_IntegralTypeSigned(type)) ? (((((type)1 << (sizeof(type)*CHAR_BIT - 2)) - 1) << 1) + 1) : ~(type)0)
/* Return the minimum value of integral type *type*. */
#define _Py_IntegralTypeMin(type) ((_Py_IntegralTypeSigned(type)) ? -_Py_IntegralTypeMax(type) - 1 : 0)
/* Check whether *v* is in the range of integral type *type*. This is most
 * useful if *v* is floating-point, since demoting a floating-point *v* to an
 * integral type that cannot represent *v*'s integral part is undefined
 * behavior. */
#define _Py_InIntegralTypeRange(type, v) (_Py_IntegralTypeMin(type) <= v && v <= _Py_IntegralTypeMax(type))

#endif /* Py_PYMATH_H */
