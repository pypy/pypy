
/* Int object interface */

#ifndef Py_EVAL_H
#define Py_EVAL_H
#ifdef __cplusplus
extern "C" {
#endif

#include "Python.h"

#define PyEval_CallObject(func,arg) \
        PyEval_CallObjectWithKeywords(func, arg, (PyObject *)NULL)

PyAPI_FUNC(PyObject *) PyEval_CallFunction(PyObject *obj, const char *format, ...);
PyAPI_FUNC(PyObject *) PyEval_CallMethod(PyObject *obj, const char *name, const char *format, ...);
PyAPI_FUNC(PyObject *) PyObject_CallFunction(PyObject *obj, char *format, ...);
PyAPI_FUNC(PyObject *) PyObject_CallMethod(PyObject *obj, char *name, char *format, ...);
PyAPI_FUNC(PyObject *) PyObject_CallFunctionObjArgs(PyObject *callable, ...);
PyAPI_FUNC(PyObject *) PyObject_CallMethodObjArgs(PyObject *callable, PyObject *name, ...);

/* These constants are also defined in cpyext/eval.py */
#define Py_single_input 256
#define Py_file_input 257
#define Py_eval_input 258

#ifdef __cplusplus
}
#endif
#endif /* !Py_EVAL_H */
