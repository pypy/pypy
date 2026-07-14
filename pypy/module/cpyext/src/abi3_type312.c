/* abi3/limited-API "type312" shims for functions PyPy does not implement.
   error shims set NotImplementedError and return an error sentinel;
   ignore shims are no-ops. */

#include "Python.h"

PyAPI_FUNC(PyObject *) PyType_FromMetaclass(PyTypeObject* _a0, PyObject* _a1, PyType_Spec* _a2, PyObject* _a3)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyType_FromMetaclass() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(Py_ssize_t) PyType_GetTypeDataSize(PyTypeObject *cls)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyType_GetTypeDataSize() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(void *) PyObject_GetTypeData(PyObject *obj, PyTypeObject *cls)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyObject_GetTypeData() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyErr_GetRaisedException(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyErr_GetRaisedException() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(void) PyErr_SetRaisedException(PyObject * _a0)
{

}

PyAPI_FUNC(void) PyErr_DisplayException(PyObject * _a0)
{

}
