#ifndef Py_PYTHON_H
#define Py_PYTHON_H

/* Compat stuff */
#ifndef _WIN32
# include <inttypes.h>
# include <stdint.h>
# include <stddef.h>
# include <limits.h>
# include <math.h>
# include <errno.h>
# include <unistd.h>
# define Py_DEPRECATED(VERSION_UNUSED) __attribute__((__deprecated__))
# define PyAPI_FUNC(RTYPE) RTYPE
# define PyAPI_DATA(RTYPE) extern RTYPE
# define Py_LOCAL_INLINE(type) static inline type
#else
# define MS_WIN32 1
# define MS_WINDOWS 1
# ifdef _MSC_VER
#  include <crtdefs.h>
# endif
# ifdef __MINGW32__
#  include <limits.h>
# endif
# include <io.h>
# define Py_DEPRECATED(VERSION_UNUSED)
# ifdef Py_BUILD_CORE
#  define PyAPI_FUNC(RTYPE) __declspec(dllexport) RTYPE
#  define PyAPI_DATA(RTYPE) extern __declspec(dllexport) RTYPE
# else
#  define PyAPI_FUNC(RTYPE) __declspec(dllimport) RTYPE
#  define PyAPI_DATA(RTYPE) extern __declspec(dllimport) RTYPE
# endif
# define Py_LOCAL_INLINE(type) static __inline type __fastcall
#endif

/* Deprecated DL_IMPORT and DL_EXPORT macros */
#ifdef _WIN32
# if defined(Py_BUILD_CORE)
#  define DL_IMPORT(RTYPE) __declspec(dllexport) RTYPE
#  define DL_EXPORT(RTYPE) __declspec(dllexport) RTYPE
# else
#  define DL_IMPORT(RTYPE) __declspec(dllimport) RTYPE
#  define DL_EXPORT(RTYPE) __declspec(dllexport) RTYPE
# endif
#endif
#ifndef DL_EXPORT
#       define DL_EXPORT(RTYPE) RTYPE
#endif
#ifndef DL_IMPORT
#       define DL_IMPORT(RTYPE) RTYPE
#endif

#include <stdlib.h>

#ifndef _WIN32
typedef intptr_t Py_ssize_t;
#else
typedef long Py_ssize_t;
#endif
#define PY_SSIZE_T_MAX ((Py_ssize_t)(((size_t)-1)>>1))
#define PY_SSIZE_T_MIN (-PY_SSIZE_T_MAX-1)
#define Py_SAFE_DOWNCAST(VALUE, WIDE, NARROW) (NARROW)(VALUE)

#define Py_USING_UNICODE

/* Convert a possibly signed character to a nonnegative int */
/* XXX This assumes characters are 8 bits wide */
#ifdef __CHAR_UNSIGNED__
#define Py_CHARMASK(c)		(c)
#else
#define Py_CHARMASK(c)		((unsigned char)((c) & 0xff))
#endif

#define statichere static

#define Py_MEMCPY memcpy

#include <pypy_macros.h>

#include "patchlevel.h"
#include "pyconfig.h"

#include "object.h"
#include "pyport.h"
#include "warnings.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <locale.h>
#include <ctype.h>

#include "boolobject.h"
#include "floatobject.h"
#include "complexobject.h"
#include "methodobject.h"
#include "funcobject.h"

#include "modsupport.h"
#include "pythonrun.h"
#include "pyerrors.h"
#include "sysmodule.h"
#include "stringobject.h"
#include "descrobject.h"
#include "tupleobject.h"
#include "dictobject.h"
#include "intobject.h"
#include "listobject.h"
#include "unicodeobject.h"
#include "compile.h"
#include "frameobject.h"
#include "eval.h"
#include "pymem.h"
#include "pycobject.h"
#include "pycapsule.h"
#include "bufferobject.h"
#include "sliceobject.h"
#include "datetime.h"
#include "pystate.h"
#include "fileobject.h"
#include "pysignals.h"
#include "pythread.h"

// XXX This shouldn't be included here
#include "structmember.h"

#include <pypy_decl.h>

/* Define macros for inline documentation. */
#define PyDoc_VAR(name) static char name[]
#define PyDoc_STRVAR(name,str) PyDoc_VAR(name) = PyDoc_STR(str)
#ifdef WITH_DOC_STRINGS
#define PyDoc_STR(str) str
#else
#define PyDoc_STR(str) ""
#endif

/* PyPy does not implement --with-fpectl */
#define PyFPE_START_PROTECT(err_string, leave_stmt)
#define PyFPE_END_PROTECT(v)

#endif
