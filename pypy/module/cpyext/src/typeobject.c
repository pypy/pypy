#include "Python.h"

PyTypeObject*
_PyPy_get_PyType_Type(void)
{
    return &PyType_Type;
}
