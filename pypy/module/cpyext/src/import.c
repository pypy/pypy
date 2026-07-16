#include <Python.h>

PyObject *
_PyImport_GetModuleAttrString(const char *modname, const char *attrname)
{
    PyObject *result;
    PyObject *mod = PyImport_ImportModule(modname);
    if (mod == NULL) {
        return NULL;
    }
    result = PyObject_GetAttrString(mod, attrname);
    Py_DECREF(mod);
    return result;
}

PyObject *
PyImport_ImportModuleLevel(const char *name, PyObject *globals, PyObject *locals,
                           PyObject *fromlist, int level)
{
    PyObject *nameobj, *mod;
    nameobj = PyUnicode_FromString(name);
    if (nameobj == NULL)
        return NULL;
    mod = PyImport_ImportModuleLevelObject(nameobj, globals, locals,
                                           fromlist, level);
    Py_DECREF(nameobj);
    return mod;
}
