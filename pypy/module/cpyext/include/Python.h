#ifndef Py_PYTHON_H
#define Py_PYTHON_H

typedef struct _object {
    long refcnt;
} PyObject;

extern PyObject *PyPy_None;
#define Py_None PyPy_None

#include <stdio.h>

#include "boolobject.h"
#include "floatobject.h"
#include "methodobject.h"

#include "modsupport.h"
#include "pythonrun.h"
#include "pyerrors.h"

#endif
