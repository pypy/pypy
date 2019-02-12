
/* Module support interface */

#ifndef Py_MODSUPPORT_H
#define Py_MODSUPPORT_H
#ifdef __cplusplus
extern "C" {
#endif

/* If PY_SSIZE_T_CLEAN is defined, each functions treats #-specifier
   to mean Py_ssize_t */
#ifdef PY_SSIZE_T_CLEAN
#undef PyArg_Parse
#undef PyArg_ParseTuple
#undef PyArg_ParseTupleAndKeywords
#undef PyArg_VaParse
#undef PyArg_VaParseTupleAndKeywords
#undef Py_BuildValue
#undef Py_VaBuildValue
#define PyArg_Parse         _PyArg_Parse_SizeT
#define PyArg_ParseTuple        _PyArg_ParseTuple_SizeT
#define PyArg_ParseTupleAndKeywords _PyArg_ParseTupleAndKeywords_SizeT
#define PyArg_VaParse           _PyArg_VaParse_SizeT
#define PyArg_VaParseTupleAndKeywords   _PyArg_VaParseTupleAndKeywords_SizeT
#define Py_BuildValue           _Py_BuildValue_SizeT
#define Py_VaBuildValue         _Py_VaBuildValue_SizeT
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

PyAPI_FUNC(int) _PyArg_Parse_SizeT(PyObject *, const char *, ...);
PyAPI_FUNC(int) _PyArg_ParseTuple_SizeT(PyObject *, const char *, ...);
PyAPI_FUNC(int) _PyArg_VaParse_SizeT(PyObject *, const char *, va_list);

PyAPI_FUNC(int) _PyArg_ParseTupleAndKeywords_SizeT(PyObject *, PyObject *,
				const char *, char **, ...);
PyAPI_FUNC(int) _PyArg_VaParseTupleAndKeywords_SizeT(PyObject *, PyObject *,
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

PyAPI_FUNC(int) PyModule_AddObject(PyObject *m, const char *name, PyObject *o);
PyAPI_FUNC(int) PyModule_AddIntConstant(PyObject *m, const char *name, long value);
PyAPI_FUNC(int) PyModule_AddStringConstant(PyObject *m, const char *name, const char *value);
#define PyModule_AddIntMacro(m, c) PyModule_AddIntConstant(m, #c, c)
#define PyModule_AddStringMacro(m, c) PyModule_AddStringConstant(m, #c, c)


PyAPI_FUNC(PyObject *) Py_BuildValue(const char *, ...);
PyAPI_FUNC(PyObject *) Py_VaBuildValue(const char *, va_list);
PyAPI_FUNC(PyObject *) _Py_BuildValue_SizeT(const char *, ...);
PyAPI_FUNC(PyObject *) _Py_VaBuildValue_SizeT(const char *, va_list);
PyAPI_FUNC(int) _PyArg_NoKeywords(const char *funcname, PyObject *kw);

PyAPI_FUNC(int) PyArg_UnpackTuple(PyObject *args, const char *name, Py_ssize_t min, Py_ssize_t max, ...);

/*
 * This is from pyport.h.  Perhaps it belongs elsewhere.
 */
#ifdef _WIN32
/* explicitly export since PyAPI_FUNC is usually dllimport */
#ifdef __cplusplus
#define PyMODINIT_FUNC extern "C" __declspec(dllexport) void
#else
#define PyMODINIT_FUNC __declspec(dllexport) void
#endif
#else
#ifdef __cplusplus
#define PyMODINIT_FUNC extern "C" PyAPI_FUNC(void)
#else
#define PyMODINIT_FUNC PyAPI_FUNC(void)
#endif
#endif /* WIN32 */

PyAPI_DATA(char *) _Py_PackageContext;

/* hack hack hack */
#ifndef __va_copy
# ifdef va_copy
#  define __va_copy(a,b) va_copy(a,b)
# endif
#endif

#ifdef __cplusplus
}
#endif
#endif /* !Py_MODSUPPORT_H */
