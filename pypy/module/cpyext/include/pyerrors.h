
/* Exception interface */

#ifndef Py_PYERRORS_H
#define Py_PYERRORS_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyExceptionClass_Check(x)                                       \
    (PyClass_Check((x)) || (PyType_Check((x)) &&                        \
      PyObject_IsSubclass((x), PyExc_BaseException)))

PyObject *PyErr_NewException(char *name, PyObject *base, PyObject *dict);
PyObject *PyErr_NewExceptionWithDoc(char *name, char *doc, PyObject *base, PyObject *dict);
PyObject *PyErr_Format(PyObject *exception, const char *format, ...);

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYERRORS_H */
