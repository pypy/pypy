#ifndef Py_PYTHON_H
#define Py_PYTHON_H

#include <pypy_rename.h>
/* Compat stuff */
#ifndef _WIN32
# include <inttypes.h>
# include <stdint.h>
# include <stddef.h>
# define Py_DEPRECATED(VERSION_UNUSED) __attribute__((__deprecated__))
# define PyAPI_DATA(RTYPE) extern RTYPE
#else
# define Py_DEPRECATED(VERSION_UNUSED)
# ifdef Py_BUILD_CORE
#  define PyAPI_DATA(RTYPE) extern __declspec(dllexport) RTYPE
# else
#  define PyAPI_DATA(RTYPE) extern __declspec(dllimport) RTYPE
# endif
#endif
#define Py_ssize_t long

#include "object.h"

/* move somewhere else */
PyAPI_DATA(PyObject *) Py_None;


#include <stdio.h>

#include "boolobject.h"
#include "floatobject.h"
#include "methodobject.h"

#include "modsupport.h"
#include "pythonrun.h"
#include "pyerrors.h"
#include "stringobject.h"
#include "descrobject.h"
#include "tupleobject.h"
#include "dictobject.h"
#include "macros.h"

#endif
