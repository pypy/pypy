#ifndef Py_PYPORT_H
#define Py_PYPORT_H

#ifdef HAVE_STDINT_H
#include <stdint.h>
#endif

/* long long is required. Ensure HAVE_LONG_LONG is defined for compatibility. */
#ifndef HAVE_LONG_LONG
#define HAVE_LONG_LONG 1
#endif
#ifndef PY_LONG_LONG
#define PY_LONG_LONG long long
/* If LLONG_MAX is defined in limits.h, use that. */
#define PY_LLONG_MIN LLONG_MIN
#define PY_LLONG_MAX LLONG_MAX
#define PY_ULLONG_MAX ULLONG_MAX
#endif

#define PY_UINT32_T uint32_t
#define PY_UINT64_T uint64_t

/* Signed variants of the above */
#define PY_INT32_T int32_t
#define PY_INT64_T int64_t


/* uintptr_t is the C9X name for an unsigned integral type such that a
 * legitimate void* can be cast to uintptr_t and then back to void* again
 * without loss of information.  Similarly for intptr_t, wrt a signed
 * integral type.
 */
typedef uintptr_t       Py_uintptr_t;
typedef intptr_t        Py_intptr_t;


/* Py_hash_t is the same size as a pointer. */
#define SIZEOF_PY_HASH_T SIZEOF_SIZE_T
typedef Py_ssize_t Py_hash_t;
/* Py_uhash_t is the unsigned equivalent needed to calculate numeric hash. */
#define SIZEOF_PY_UHASH_T SIZEOF_SIZE_T
typedef size_t Py_uhash_t;

/* Largest possible value of size_t. */
#define PY_SIZE_MAX SIZE_MAX

/* Largest positive value of type Py_ssize_t. */
#define PY_SSIZE_T_MAX ((Py_ssize_t)(((size_t)-1)>>1))
/* Smallest negative value of type Py_ssize_t. */
#define PY_SSIZE_T_MIN (-PY_SSIZE_T_MAX-1)

#include <stdarg.h>

/* CPython needs this for the c-extension datetime, which is pure python on PyPy
   downstream packages assume it is here (Pandas for instance) */
#include <time.h>

/*******************************
 * stat() and fstat() fiddling *
 *******************************/

/* We expect that stat and fstat exist on most systems.
 *  It's confirmed on Unix, Mac and Windows.
 *  If you don't have them, add
 *      #define DONT_HAVE_STAT
 * and/or
 *      #define DONT_HAVE_FSTAT
 * to your pyconfig.h. Python code beyond this should check HAVE_STAT and
 * HAVE_FSTAT instead.
 * Also
 *      #define HAVE_SYS_STAT_H
 * if <sys/stat.h> exists on your platform, and
 *      #define HAVE_STAT_H
 * if <stat.h> does.
 */
#ifndef DONT_HAVE_STAT
#define HAVE_STAT
#endif

#ifndef DONT_HAVE_FSTAT
#define HAVE_FSTAT
#endif

#ifdef RISCOS
#include <sys/types.h>
#include "unixstuff.h"
#endif

#ifdef HAVE_SYS_STAT_H
#if defined(PYOS_OS2) && defined(PYCC_GCC)
#include <sys/types.h>
#endif
#include <sys/stat.h>
#elif defined(HAVE_STAT_H)
#include <stat.h>
#else
#endif

/*
 * Hide GCC attributes from compilers that don't support them.
 */
#if (!defined(__GNUC__) || __GNUC__ < 2 || \
     (__GNUC__ == 2 && __GNUC_MINOR__ < 7) )
#define Py_GCC_ATTRIBUTE(x)
#else
#define Py_GCC_ATTRIBUTE(x) __attribute__(x)
#endif

/*
 * Specify alignment on compilers that support it.
 */
#if defined(__GNUC__) && __GNUC__ >= 3
#define Py_ALIGNED(x) __attribute__((aligned(x)))
#else
#define Py_ALIGNED(x)
#endif

/* Eliminate end-of-loop code not reached warnings from SunPro C
 * when using do{...}while(0) macros
 */
#ifdef __SUNPRO_C
#pragma error_messages (off,E_END_OF_LOOP_CODE_NOT_REACHED)
#endif

#ifndef Py_LL
#define Py_LL(x) x##LL
#endif

#ifndef Py_ULL
#define Py_ULL(x) Py_LL(x##U)
#endif

#define Py_VA_COPY va_copy


#endif /* Py_PYPORT_H */
