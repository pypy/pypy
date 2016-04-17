
/* NDArray object interface - S. H. Muller, 2013/07/26 */
/* For testing ndarrayobject only */

#ifndef Py_NDARRAYOBJECT_H
#define Py_NDARRAYOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#include "npy_common.h"
#include "ndarraytypes.h"

/* fake PyArrayObject so that code that doesn't do direct field access works */
#define PyArrayObject PyObject
#define PyArray_Descr PyObject

PyAPI_DATA(PyTypeObject) PyArray_Type;

#define PyArray_SimpleNew _PyArray_SimpleNew
#define PyArray_ZEROS _PyArray_ZEROS
#define PyArray_CopyInto _PyArray_CopyInto
#define PyArray_FILLWBYTE _PyArray_FILLWBYTE

#define NPY_MAXDIMS 32

/* functions defined in ndarrayobject.c*/

PyAPI_FUNC(void) _PyArray_FILLWBYTE(PyObject* obj, int val);
PyAPI_FUNC(PyObject *) _PyArray_ZEROS(int nd, npy_intp* dims, int type_num, int fortran);
PyAPI_FUNC(int) _PyArray_CopyInto(PyArrayObject* dest, PyArrayObject* src);



#ifdef __cplusplus
}
#endif
#endif /* !Py_NDARRAYOBJECT_H */
