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

#endif /* Py_PYPORT_H */
