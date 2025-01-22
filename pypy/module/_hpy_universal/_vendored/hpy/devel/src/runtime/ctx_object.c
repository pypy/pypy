#include <Python.h>
#include "hpy.h"

#ifndef HPY_ABI_CPYTHON
   // for _h2py and _py2h
#  include "handles.h"
#endif


_HPy_HIDDEN void
ctx_Dump(HPyContext *ctx, HPy h)
{
    // just use _PyObject_Dump for now, but we might want to add more info
    // about the handle itself in the future.
    _PyObject_Dump(_h2py(h));
}

_HPy_HIDDEN HPy
ctx_Type(HPyContext *ctx, HPy obj)
{
    PyTypeObject *tp = Py_TYPE(_h2py(obj));
    Py_INCREF(tp);
    return _py2h((PyObject *)tp);
}

/* NOTE: In contrast to CPython, HPy has to check that 'h_type' is a type. This
   is not necessary on CPython because it requires C type 'PyTypeObject *' but
   here we can only receive an HPy handle. Appropriate checking of the argument
   will be done in the debug mode.
*/
_HPy_HIDDEN int
ctx_TypeCheck(HPyContext *ctx, HPy h_obj, HPy h_type)
{
    return PyObject_TypeCheck(_h2py(h_obj), (PyTypeObject*)_h2py(h_type));
}

_HPy_HIDDEN int
ctx_Is(HPyContext *ctx, HPy h_obj, HPy h_other)
{
    return _h2py(h_obj) == _h2py(h_other);
}

_HPy_HIDDEN HPy
ctx_GetItem_i(HPyContext *ctx, HPy obj, HPy_ssize_t idx) {
    PyObject *py_obj = _h2py(obj);
    if (PySequence_Check(py_obj)) {
        return _py2h(PySequence_GetItem(py_obj, idx));
    }
    PyObject* key = PyLong_FromSsize_t(idx);
    if (key == NULL)
        return HPy_NULL;
    HPy result = _py2h(PyObject_GetItem(py_obj, key));
    Py_DECREF(key);
    return result;
}

_HPy_HIDDEN HPy
ctx_GetItem_s(HPyContext *ctx, HPy obj, const char *key) {
    PyObject* key_o = PyUnicode_FromString(key);
    if (key_o == NULL)
        return HPy_NULL;
    HPy result = _py2h(PyObject_GetItem(_h2py(obj), key_o));
    Py_DECREF(key_o);
    return result;
}

_HPy_HIDDEN int
ctx_SetItem_i(HPyContext *ctx, HPy obj, HPy_ssize_t idx, HPy value) {
    PyObject* key = PyLong_FromSsize_t(idx);
    if (key == NULL)
        return -1;
    int result = PyObject_SetItem(_h2py(obj), key, _h2py(value));
    Py_DECREF(key);
    return result;
}

_HPy_HIDDEN int
ctx_SetItem_s(HPyContext *ctx, HPy obj, const char *key, HPy value) {
    PyObject* key_o = PyUnicode_FromString(key);
    if (key_o == NULL)
        return -1;
    int result = PyObject_SetItem(_h2py(obj), key_o, _h2py(value));
    Py_DECREF(key_o);
    return result;
}

_HPy_HIDDEN int
ctx_DelItem_i(HPyContext *ctx, HPy obj, HPy_ssize_t idx) {
    PyObject* key = PyLong_FromSsize_t(idx);
    if (key == NULL)
        return -1;
    int result = PyObject_DelItem(_h2py(obj), key);
    Py_DECREF(key);
    return result;
}

_HPy_HIDDEN int
ctx_DelItem_s(HPyContext *ctx, HPy obj, const char *key) {
    PyObject* key_o = PyUnicode_FromString(key);
    if (key_o == NULL)
        return -1;
    int result = PyObject_DelItem(_h2py(obj), key_o);
    Py_DECREF(key_o);
    return result;
}
