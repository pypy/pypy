#include "common_header.h"
#include <src/pyobj.h>

/************************************************************/
/***  C header subsection: untyped operations             ***/
/***  as OP_XXX() macros calling the CPython API          ***/
#ifdef PYPY_CPYTHON_EXTENSION

#if (PY_VERSION_HEX < 0x02040000)

unsigned long RPyLong_AsUnsignedLong(PyObject *v) 
{
	if (PyInt_Check(v)) {
		long val = PyInt_AsLong(v);
		if (val < 0) {
			PyErr_SetNone(PyExc_OverflowError);
			return (unsigned long)-1;
		}
		return val;
        } else {
		return PyLong_AsUnsignedLong(v);
	}
}

#else
#define RPyLong_AsUnsignedLong PyLong_AsUnsignedLong
#endif


unsigned long long RPyLong_AsUnsignedLongLong(PyObject *v)
{
	if (PyInt_Check(v))
		return PyInt_AsLong(v);
	else
		return PyLong_AsUnsignedLongLong(v);
}

long long RPyLong_AsLongLong(PyObject *v)
{
	if (PyInt_Check(v))
		return PyInt_AsLong(v);
	else
		return PyLong_AsLongLong(v);
}

#endif  /* PYPY_CPYTHON_EXTENSION */
