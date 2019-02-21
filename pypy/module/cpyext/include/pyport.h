#ifndef Py_PYPORT_H
#define Py_PYPORT_H

#ifdef HAVE_STDINT_H
#include <stdint.h>
#endif

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

/* uintptr_t is the C9X name for an unsigned integral type such that a
 * legitimate void* can be cast to uintptr_t and then back to void* again
 * without loss of information.  Similarly for intptr_t, wrt a signed
 * integral type.
 */
#ifdef HAVE_UINTPTR_T
typedef uintptr_t   Py_uintptr_t;
typedef intptr_t    Py_intptr_t;

#elif SIZEOF_VOID_P <= SIZEOF_INT
typedef unsigned int    Py_uintptr_t;
typedef int     Py_intptr_t;

#elif SIZEOF_VOID_P <= SIZEOF_LONG
typedef unsigned long   Py_uintptr_t;
typedef long        Py_intptr_t;

#elif defined(HAVE_LONG_LONG) && (SIZEOF_VOID_P <= SIZEOF_LONG_LONG)
typedef unsigned PY_LONG_LONG   Py_uintptr_t;
typedef PY_LONG_LONG        Py_intptr_t;

#else
#   error "Python needs a typedef for Py_uintptr_t in pyport.h."
#endif /* HAVE_UINTPTR_T */

/* Py_hash_t is the same size as a pointer. */
#define SIZEOF_PY_HASH_T SIZEOF_SIZE_T
typedef Py_ssize_t Py_hash_t;
/* Py_uhash_t is the unsigned equivalent needed to calculate numeric hash. */
#define SIZEOF_PY_UHASH_T SIZEOF_SIZE_T
typedef size_t Py_uhash_t;

#include <stdarg.h>

#ifdef __va_copy
#define Py_VA_COPY __va_copy
#else
#ifdef VA_LIST_IS_ARRAY
#define Py_VA_COPY(x, y) Py_MEMCPY((x), (y), sizeof(va_list))
#else
#define Py_VA_COPY(x, y) (x) = (y)
#endif
#endif

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
