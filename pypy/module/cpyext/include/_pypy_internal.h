#ifndef PyPy_INTERNAL_H
#define PyPy_INTERNAL_H

#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

PyAPI_FUNC(PyTypeObject*) _PyPy_get_PyType_Type(void);
PyAPI_FUNC(PyObject*) _PyPy_get_PyExc_MemoryError(void);

    
#ifdef __cplusplus
}
#endif
#endif /* !PyPy_INTERNAL_H */
