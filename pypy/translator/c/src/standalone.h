/* XXX for now we always include Python.h even to produce stand-alone
 * executables (which are *not* linked against CPython then),
 * to get the convenient macro definitions
 */
#define Py_BUILD_CORE  /* for Windows: avoid pulling libs in */
#include "Python.h"

#include <stdlib.h>
#include <limits.h>
#include <assert.h>
#include <math.h>

#define PyObject_Malloc malloc
#define PyObject_Free   free

#ifdef MS_WINDOWS
#  ifdef _MSC_VER
#    pragma warning(disable: 4033 4102 4101 4716) /*suppress a few warnings*/
#  endif
#endif
