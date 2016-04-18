
#include "Python.h"
#include "pypy_numpy.h"
#include "numpy/arrayobject.h"
#include <string.h>   /* memset, memcpy */

void 
_PyArray_FILLWBYTE(PyObject* obj, int val) {
    memset(_PyArray_DATA(obj), val, _PyArray_NBYTES(obj));
}

PyObject* 
_PyArray_ZEROS(int nd, npy_intp* dims, int type_num, int fortran) 
{
    PyObject *arr = _PyArray_SimpleNew(nd, dims, type_num);
    memset(_PyArray_DATA(arr), 0, _PyArray_NBYTES(arr));
    return arr;
}

int 
_PyArray_CopyInto(PyArrayObject* dest, PyArrayObject* src)
{
    memcpy(_PyArray_DATA(dest), _PyArray_DATA(src), _PyArray_NBYTES(dest));
    return 0;
}

