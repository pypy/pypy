
/* Exception interface */

#ifndef Py_PYERRORS_H
#define Py_PYERRORS_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_FUNC(PyObject *) PyErr_NewException(char *name, PyObject *base, PyObject *dict);
PyAPI_FUNC(PyObject *) PyErr_Format(PyObject *exception, const char *format, ...);

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYERRORS_H */
