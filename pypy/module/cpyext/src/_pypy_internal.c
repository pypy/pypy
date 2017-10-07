#include "Python.h"

PyTypeObject*
_PyPy_get_PyType_Type(void)
{
    return &PyType_Type;
}

PyObject*
_PyPy_get_PyExc_MemoryError(void)
{
    return PyExc_MemoryError;
}
