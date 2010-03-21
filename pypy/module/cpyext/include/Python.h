#ifndef Py_PYTHON_H
#define Py_PYTHON_H

/* Compat stuff */
#ifndef _WIN32
#include <inttypes.h>
#include <stdint.h>
#include <stddef.h>
#define Py_DEPRECATED(VERSION_UNUSED) __attribute__((__deprecated__))
#else
#define Py_DEPRECATED(VERSION_UNUSED)
#endif
#define Py_ssize_t long

#include "object.h"

/* move somewhere else */
extern PyObject *Py_None;


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
