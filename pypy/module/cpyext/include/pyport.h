#ifndef Py_PYPORT_H
#define Py_PYPORT_H

#ifdef HAVE_STDINT_H
#include <stdint.h>
#endif

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

#endif /* Py_PYPORT_H */
