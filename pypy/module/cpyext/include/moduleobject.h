/* Module object interface */

#ifndef Py_MODULEOBJECT_H
#define Py_MODULEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#include "cpyext_moduleobject.h"

PyAPI_FUNC(PyObject *) PyModuleDef_Init(struct PyModuleDef*);

#ifdef __cplusplus
}
#endif
#endif /* !Py_MODULEOBJECT_H */
