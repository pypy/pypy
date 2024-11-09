// Entry point of the Python C API.
// C extensions should only #include <Python.h>, and not include directly
// the other Python header files included by <Python.h>.

#ifndef Py_PYTHON_H
#define Py_PYTHON_H

// Since this is a "meta-include" file, no #ifdef __cplusplus / extern "C" {

// Include Python header files
#include "patchlevel.h"
#include <pyconfig.h>

/* Compat stuff */
#ifdef __GNUC__
#define _GNU_SOURCE 1
#endif
#ifndef _WIN32
# include <stddef.h>
# include <errno.h>
# include <unistd.h>
#else
# include <sys/types.h>   /* for 'off_t' */
#endif
#include <stdio.h>

#include <string.h>
#include <stdlib.h>

#define Py_USING_UNICODE

#define statichere static

#include "pyport.h"

#include "pypy_macros.h"
#include "pymacro.h"

#include "pymath.h"
#include "pymem.h"

#include "object.h"
#include "objimpl.h"
#include "typeslots.h"
#include "pyhash.h"
#include "pytime.h"
#include "warnings.h"

#include <stdarg.h>
#include <assert.h>
#include <locale.h>
#include <ctype.h>

#include "bytearrayobject.h"
#include "bytesobject.h"
#include "unicodeobject.h"
#include "longobject.h"
#include "boolobject.h"
#include "floatobject.h"
#include "complexobject.h"
#include "memoryobject.h"
#include "tupleobject.h"
#include "listobject.h"
#include "dictobject.h"
#include "setobject.h"
#include "methodobject.h"
#include "moduleobject.h"
#include "funcobject.h"
#include "fileobject.h"
#include "pycapsule.h"
#include "code.h"
#include "traceback.h"
#include "sliceobject.h"
#include "genobject.h"
#include "descrobject.h"
#include "genericaliasobject.h"
#include "structseq.h"
#include "pyerrors.h"
#include "pythread.h"
#include "pystate.h"

#include "modsupport.h"
#include "compile.h"
#include "pythonrun.h"
#include "pylifecycle.h"
#include "ceval.h"
#include "sysmodule.h"
#include "import.h"

#include "abstract.h"

#include "pystrtod.h"

/* Not in CPython */
#include "frameobject.h"
#include "datetime.h"
#include "pysignals.h"

/* Missing definitions */
#include "missing.h"

/* The declarations of most API functions are generated in a separate file */
/* Don't include them while building PyPy, RPython also generated signatures
 * which are similar but not identical. */
#ifndef PYPY_STANDALONE
#ifdef __cplusplus
extern "C" {
#endif
  #include "pypy_decl.h"
#ifdef __cplusplus
}
#endif
#endif  /* PYPY_STANDALONE */

/* Define macros for inline documentation. */
#define PyDoc_STRVAR(name,str) PyDoc_VAR(name) = PyDoc_STR(str)
#ifdef WITH_DOC_STRINGS
#define PyDoc_STR(str) str
#else
#define PyDoc_STR(str) ""
#endif

/* PyPy does not implement --with-fpectl */
#define PyFPE_START_PROTECT(err_string, leave_stmt)
#define PyFPE_END_PROTECT(v)


#endif /* !Py_PYTHON_H */
