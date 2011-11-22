
/* Module support interface */

#ifndef Py_MODSUPPORT_H
#define Py_MODSUPPORT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PYTHON_API_VERSION 1013
#define PYTHON_API_STRING "1013"

int PyArg_Parse(PyObject *, const char *, ...);
int PyArg_ParseTuple(PyObject *, const char *, ...);
int PyArg_VaParse(PyObject *, const char *, va_list);

int PyArg_ParseTupleAndKeywords(PyObject *, PyObject *,
				const char *, char **, ...);
int PyArg_VaParseTupleAndKeywords(PyObject *, PyObject *,
				const char *, char **, va_list);
  
/* to make sure that modules compiled with CPython's or PyPy's Python.h
   are not importable on the other interpreter, use a #define to expect a
   different symbol: (this function is implemented in ../modsupport.py) */
#define Py_InitModule4 _Py_InitPyPyModule

#define Py_InitModule(name, methods) \
	Py_InitModule4(name, methods, (char *)NULL, (PyObject *)NULL, \
		       PYTHON_API_VERSION)

#define Py_InitModule3(name, methods, doc) \
	Py_InitModule4(name, methods, doc, (PyObject *)NULL, \
		       PYTHON_API_VERSION)

int PyModule_AddObject(PyObject *m, const char *name, PyObject *o);
int PyModule_AddIntConstant(PyObject *m, const char *name, long value);
int PyModule_AddStringConstant(PyObject *m, const char *name, const char *value);


PyObject * Py_BuildValue(const char *, ...);
PyObject * Py_VaBuildValue(const char *, va_list);
PyObject * _Py_BuildValue_SizeT(const char *, ...);
PyObject * _Py_VaBuildValue_SizeT(const char *, va_list);
int _PyArg_NoKeywords(const char *funcname, PyObject *kw);

int PyArg_UnpackTuple(PyObject *args, const char *name, Py_ssize_t min, Py_ssize_t max, ...);

/*
 * This is from pyport.h.  Perhaps it belongs elsewhere.
 */
#ifdef __cplusplus
#define PyMODINIT_FUNC extern "C" void
#else
#define PyMODINIT_FUNC void
#endif


#ifdef __cplusplus
}
#endif
#endif /* !Py_MODSUPPORT_H */
