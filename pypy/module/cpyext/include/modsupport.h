
/* Module support interface */

#ifndef Py_MODSUPPORT_H
#define Py_MODSUPPORT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PYTHON_API_VERSION 1013
#define PYTHON_API_STRING "1013"

PyAPI_FUNC(int) PyArg_Parse(PyObject *, const char *, ...);
PyAPI_FUNC(int) PyArg_ParseTuple(PyObject *, const char *, ...);
PyAPI_FUNC(int) PyArg_VaParse(PyObject *, const char *, va_list);

PyAPI_FUNC(int) PyArg_ParseTupleAndKeywords(PyObject *, PyObject *,
                                            const char *, char **, ...);
PyAPI_FUNC(int) PyArg_VaParseTupleAndKeywords(PyObject *, PyObject *,
                                              const char *, char **, va_list);

#define Py_InitModule(name, methods) \
        Py_InitModule4(name, methods, (char *)NULL, (PyObject *)NULL, \
                       PYTHON_API_VERSION)

#define Py_InitModule3(name, methods, doc) \
        Py_InitModule4(name, methods, doc, (PyObject *)NULL, \
                       PYTHON_API_VERSION)

PyAPI_FUNC(int) PyModule_AddObject(PyObject *m, const char *name, PyObject *o);
PyAPI_FUNC(int) PyModule_AddIntConstant(PyObject *m, const char *name, long value);
PyAPI_FUNC(int) PyModule_AddStringConstant(PyObject *m, const char *name, const char *value);


PyAPI_FUNC(PyObject *) Py_BuildValue(const char *, ...);
PyAPI_FUNC(PyObject *) _Py_BuildValue_SizeT(const char *, ...);
PyAPI_FUNC(PyObject *) Py_VaBuildValue(const char *, va_list va);
PyAPI_FUNC(PyObject *) _Py_VaBuildValue_SizeT(const char *, va_list va);
PyAPI_FUNC(int) _PyArg_NoKeywords(const char *funcname, PyObject *kw);

PyAPI_FUNC(int) PyArg_UnpackTuple(PyObject *args, const char *name, Py_ssize_t min, Py_ssize_t max, ...);

/*
 * This is from pyport.h.  Perhaps it belongs elsewhere.
 */
#define PyMODINIT_FUNC void


#ifdef __cplusplus
}
#endif
#endif /* !Py_MODSUPPORT_H */
