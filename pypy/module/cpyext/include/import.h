
/* Module definition and import interface */

#ifndef Py_IMPORT_H
#define Py_IMPORT_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_FUNC(PyObject *) PyImport_ImportModuleLevel(
    const char *name,           /* UTF-8 encoded string */
    PyObject *globals,
    PyObject *locals,
    PyObject *fromlist,
    int level
    );

#define PyImport_ImportModuleEx(n, g, l, f) \
    PyImport_ImportModuleLevel(n, g, l, f, 0)

PyAPI_FUNC(PyObject *) _PyImport_GetModuleAttrString(const char *modname,
                                                     const char *attrname);

/* abi3/limited-API shims */
PyAPI_FUNC(PyObject *) PyImport_AddModuleObject(PyObject *name);
PyAPI_FUNC(int) PyImport_AppendInittab(const char *name,  PyObject* (*initfunc)(void));
PyAPI_FUNC(PyObject *) PyImport_ExecCodeModuleObject(PyObject *name, PyObject *co, PyObject *pathname, PyObject *cpathname);
PyAPI_FUNC(PyObject *) PyImport_ExecCodeModuleWithPathnames(const char *name,  PyObject *co, const char *pathname,  const char *cpathname);
PyAPI_FUNC(PyObject *) PyImport_GetImporter(PyObject *path);
PyAPI_FUNC(long) PyImport_GetMagicNumber(void);
PyAPI_FUNC(const char *) PyImport_GetMagicTag(void);
PyAPI_FUNC(int) PyImport_ImportFrozenModule(const char *name);
PyAPI_FUNC(int) PyImport_ImportFrozenModuleObject(PyObject *name);

#ifdef __cplusplus
}
#endif
#endif /* !Py_IMPORT_H */
