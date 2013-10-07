
#include "Python.h"
#include "numpy/arrayobject.h"
#include <string.h>   /* memset, memcpy */

PyTypeObject PyArray_Type;

void 
_PyArray_FILLWBYTE(PyObject* obj, int val) {
    memset(PyArray_DATA(obj), val, PyArray_NBYTES(obj));
}

PyObject* 
_PyArray_ZEROS(int nd, npy_intp* dims, int type_num, int fortran) 
{
    PyObject *arr = PyArray_EMPTY(nd, dims, type_num, fortran);
    memset(PyArray_DATA(arr), 0, PyArray_NBYTES(arr));
    return arr;
}

int 
_PyArray_CopyInto(PyArrayObject* dest, PyArrayObject* src)
{
    memcpy(PyArray_DATA(dest), PyArray_DATA(src), PyArray_NBYTES(dest));
    return 0;
}

