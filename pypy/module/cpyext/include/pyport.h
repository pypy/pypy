#ifndef Py_PYPORT_H
#define Py_PYPORT_H

#include "pyconfig.h" /* include for defines */

#include <inttypes.h>

/**************************************************************************
Symbols and macros to supply platform-independent interfaces to basic
C language & library operations whose spellings vary across platforms.

Please try to make documentation here as clear as possible:  by definition,
the stuff here is trying to illuminate C's darkest corners.

Config #defines referenced here:

SIGNED_RIGHT_SHIFT_ZERO_FILLS
Meaning:  To be defined iff i>>j does not extend the sign bit when i is a
          signed integral type and i < 0.
Used in:  Py_ARITHMETIC_RIGHT_SHIFT

Py_DEBUG
Meaning:  Extra checks compiled in for debug mode.
Used in:  Py_SAFE_DOWNCAST

**************************************************************************/

/* typedefs for some C9X-defined synonyms for integral types.
 *
 * The names in Python are exactly the same as the C9X names, except with a
 * Py_ prefix.  Until C9X is universally implemented, this is the only way
 * to ensure that Python gets reliable names that don't conflict with names
 * in non-Python code that are playing their own tricks to define the C9X
 * names.
 *
 * NOTE: don't go nuts here!  Python has no use for *most* of the C9X
 * integral synonyms.  Only define the ones we actually need.
 */

/* typedefs for some C9X-defined synonyms for integral types. */
#ifdef HAVE_LONG_LONG
#ifndef PY_LONG_LONG
#define PY_LONG_LONG long long
#if defined(LLONG_MAX)
/* If LLONG_MAX is defined in limits.h, use that. */
#define PY_LLONG_MIN LLONG_MIN
#define PY_LLONG_MAX LLONG_MAX
#define PY_ULLONG_MAX ULLONG_MAX
#elif defined(__LONG_LONG_MAX__)
/* Otherwise, if GCC has a builtin define, use that. */
#define PY_LLONG_MAX __LONG_LONG_MAX__
#define PY_LLONG_MIN (-PY_LLONG_MAX-1)
#define PY_ULLONG_MAX (__LONG_LONG_MAX__*2ULL + 1ULL)
#else
/* Otherwise, rely on two's complement. */
#define PY_ULLONG_MAX (~0ULL)
#define PY_LLONG_MAX  ((long long)(PY_ULLONG_MAX>>1))
#define PY_LLONG_MIN (-PY_LLONG_MAX-1)
#endif /* LLONG_MAX */
#endif
#endif /* HAVE_LONG_LONG */

/* a build with 30-bit digits for Python long integers needs an exact-width
 * 32-bit unsigned integer type to store those digits.  (We could just use
 * type 'unsigned long', but that would be wasteful on a system where longs
 * are 64-bits.)  On Unix systems, the autoconf macro AC_TYPE_UINT32_T defines
 * uint32_t to be such a type unless stdint.h or inttypes.h defines uint32_t.
 * However, it doesn't set HAVE_UINT32_T, so we do that here.
 */
#ifdef uint32_t
#define HAVE_UINT32_T 1
#endif

#ifdef HAVE_UINT32_T
#ifndef PY_UINT32_T
#define PY_UINT32_T uint32_t
#endif
#endif

/* Macros for a 64-bit unsigned integer type; used for type 'twodigits' in the
 * long integer implementation, when 30-bit digits are enabled.
 */
#ifdef uint64_t
#define HAVE_UINT64_T 1
#endif

#ifdef HAVE_UINT64_T
#ifndef PY_UINT64_T
#define PY_UINT64_T uint64_t
#endif
#endif

/* Signed variants of the above */
#ifdef int32_t
#define HAVE_INT32_T 1
#endif

#ifdef HAVE_INT32_T
#ifndef PY_INT32_T
#define PY_INT32_T int32_t
#endif
#endif

#ifdef int64_t
#define HAVE_INT64_T 1
#endif

#ifdef HAVE_INT64_T
#ifndef PY_INT64_T
#define PY_INT64_T int64_t
#endif
#endif

/* uintptr_t is the C9X name for an unsigned integral type such that a
 * legitimate void* can be cast to uintptr_t and then back to void* again
 * without loss of information.  Similarly for intptr_t, wrt a signed
 * integral type.
 */
#ifdef HAVE_UINTPTR_T
typedef uintptr_t       Py_uintptr_t;
typedef intptr_t        Py_intptr_t;

#elif SIZEOF_VOID_P <= SIZEOF_INT
typedef unsigned int    Py_uintptr_t;
typedef int             Py_intptr_t;

#elif SIZEOF_VOID_P <= SIZEOF_LONG
typedef unsigned long   Py_uintptr_t;
typedef long            Py_intptr_t;

#elif defined(HAVE_LONG_LONG) && (SIZEOF_VOID_P <= SIZEOF_LONG_LONG)
typedef unsigned PY_LONG_LONG   Py_uintptr_t;
typedef PY_LONG_LONG            Py_intptr_t;

#else
#   error "Python needs a typedef for Py_uintptr_t in pyport.h."
#endif /* HAVE_UINTPTR_T */

/* Largest possible value of size_t.
   SIZE_MAX is part of C99, so it might be defined on some
   platforms. If it is not defined, (size_t)-1 is a portable
   definition for C89, due to the way signed->unsigned
   conversion is defined. */
#ifdef SIZE_MAX
#define PY_SIZE_MAX SIZE_MAX
#else
#define PY_SIZE_MAX ((size_t)-1)
#endif

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
     (__GNUC__ == 2 && __GNUC_MINOR__ < 7) ) && \
    !defined(RISCOS)
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

/*
 * Older Microsoft compilers don't support the C99 long long literal suffixes,
 * so these will be defined in PC/pyconfig.h for those compilers.
 */
#ifndef Py_LL
#define Py_LL(x) x##LL
#endif

#ifndef Py_ULL
#define Py_ULL(x) Py_LL(x##U)
#endif

#endif /* Py_PYPORT_H */
