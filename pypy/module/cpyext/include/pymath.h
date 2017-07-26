#ifndef Py_PYMATH_H
#define Py_PYMATH_H

/**************************************************************************
Symbols and macros to supply platform-independent interfaces to mathematical
functions and constants
**************************************************************************/

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

/* Py_NAN
 * A value that evaluates to a NaN. On IEEE 754 platforms INF*0 or
 * INF/INF works. Define Py_NO_NAN in pyconfig.h if your platform
 * doesn't support NaNs.
 */
#if !defined(Py_NAN) && !defined(Py_NO_NAN)
#if !defined(__INTEL_COMPILER)
    #define Py_NAN (Py_HUGE_VAL * 0.)
#else /* __INTEL_COMPILER */
    #if defined(ICC_NAN_STRICT)
        #pragma float_control(push)
        #pragma float_control(precise, on)
        #pragma float_control(except,  on)
        #if defined(_MSC_VER)
            __declspec(noinline)
        #else /* Linux */
            __attribute__((noinline))
        #endif /* _MSC_VER */
        static double __icc_nan()
        {
            return sqrt(-1.0);
        }
        #pragma float_control (pop)
        #define Py_NAN __icc_nan()
    #else /* ICC_NAN_RELAXED as default for Intel Compiler */
        static union { unsigned char buf[8]; double __icc_nan; } __nan_store = {0,0,0,0,0,0,0xf8,0x7f};
        #define Py_NAN (__nan_store.__icc_nan)
    #endif /* ICC_NAN_STRICT */
#endif /* __INTEL_COMPILER */
#endif

#endif /* Py_PYMATH_H */
