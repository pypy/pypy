#ifndef Py_PYTHON_H
#define Py_PYTHON_H

/* Compat stuff */
#include <inttypes.h>
#include <stdint.h>
#define Py_ssize_t long
#define Py_DEPRECATED(VERSION_UNUSED) __attribute__((__deprecated__))

#include "object.h"

/* move somewhere else */
extern PyObject *PyPy_None;
#define Py_None PyPy_None

#define long int /* XXX: same hack as in api.py */

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
