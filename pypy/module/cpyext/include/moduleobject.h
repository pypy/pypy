/* Module object interface */

#ifndef Py_MODULEOBJECT_H
#define Py_MODULEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#include "cpyext_moduleobject.h"

PyAPI_FUNC(struct PyModuleDef*) PyModule_GetDef(PyObject*);
PyAPI_FUNC(void*) PyModule_GetState(PyObject*);


PyAPI_FUNC(PyObject *) PyModuleDef_Init(struct PyModuleDef*);

/* for Py_mod_multiple_interpreters: */
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 >= 0x030c0000
#  define Py_MOD_MULTIPLE_INTERPRETERS_NOT_SUPPORTED ((void *)0)
#  define Py_MOD_MULTIPLE_INTERPRETERS_SUPPORTED ((void *)1)
#  define Py_MOD_PER_INTERPRETER_GIL_SUPPORTED ((void *)2)
#endif



/* abi3/limited-API shims */
PyAPI_FUNC(const char *) PyModule_GetFilename(PyObject *);

#ifdef __cplusplus
}
#endif
#endif /* !Py_MODULEOBJECT_H */
