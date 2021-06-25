#include "common/autogen_impl.h"

/* object.h */

HPyAPI_STORAGE HPy
_HPy_IMPL_NAME_NOPREFIX(GetItem_i)(HPyContext ctx, HPy obj, HPy_ssize_t idx) {
    PyObject* key = PyLong_FromSsize_t(idx);
    if (key == NULL)
        return HPy_NULL;
    HPy result = _py2h(PyObject_GetItem(_h2py(obj), key));
    Py_DECREF(key);
    return result;
}

HPyAPI_STORAGE HPy
_HPy_IMPL_NAME_NOPREFIX(GetItem_s)(HPyContext ctx, HPy obj, const char *key) {
    PyObject* key_o = PyUnicode_FromString(key);
    if (key_o == NULL)
        return HPy_NULL;
    HPy result = _py2h(PyObject_GetItem(_h2py(obj), key_o));
    Py_DECREF(key_o);
    return result;
}

HPyAPI_STORAGE int
_HPy_IMPL_NAME_NOPREFIX(SetItem_i)(HPyContext ctx, HPy obj, HPy_ssize_t idx, HPy value) {
    PyObject* key = PyLong_FromSsize_t(idx);
    if (key == NULL)
        return -1;
    int result = PyObject_SetItem(_h2py(obj), key, _h2py(value));
    Py_DECREF(key);
    return result;
}

HPyAPI_STORAGE int
_HPy_IMPL_NAME_NOPREFIX(SetItem_s)(HPyContext ctx, HPy obj, const char *key, HPy value) {
    PyObject* key_o = PyUnicode_FromString(key);
    if (key_o == NULL)
        return -1;
    int result = PyObject_SetItem(_h2py(obj), key_o, _h2py(value));
    Py_DECREF(key_o);
    return result;
}

HPyAPI_STORAGE int
_HPy_IMPL_NAME(Err_Occurred)(HPyContext ctx) {
    return PyErr_Occurred() ? 1 : 0;
}
