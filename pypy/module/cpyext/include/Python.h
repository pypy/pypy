#ifndef Py_PYTHON_H
#define Py_PYTHON_H

#include <inttypes.h>
#include <stdint.h>
typedef long             Py_ssize_t;
#define Py_DEPRECATED(VERSION_UNUSED) __attribute__((__deprecated__))

#include "object.h"

extern PyObject *PyPy_None;
#define Py_None PyPy_None

#include <stdio.h>

#include "boolobject.h"
#include "floatobject.h"
#include "methodobject.h"

#include "modsupport.h"
#include "pythonrun.h"
#include "pyerrors.h"
#include "stringobject.h"
#include "descrobject.h"

#endif
