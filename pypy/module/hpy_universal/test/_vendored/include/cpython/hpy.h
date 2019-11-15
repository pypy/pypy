#ifndef HPy_CPYTHON_H
#define HPy_CPYTHON_H




/* XXX: it would be nice if we could include hpy.h WITHOUT bringing in all the
   stuff from Python.h, to make sure that people don't use the CPython API by
   mistake. How to achieve it, though? */

/* XXX: should we:
 *    - enforce PY_SSIZE_T_CLEAN in hpy
 *    - make it optional
 *    - make it the default but give a way to disable it?
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

#ifdef __GNUC__
#define HPyAPI_FUNC(restype)  __attribute__((unused)) static inline restype
#else
#define HPyAPI_FUNC(restype)  static inline restype
#endif


typedef struct { PyObject *_o; } HPy;
typedef long HPyContext;

HPyAPI_FUNC(HPyContext)
_HPyGetContext(void) {
    return 42;
}

/* For internal usage only. These should be #undef at the end of this header.
   If you need to convert HPy to PyObject* and vice-versa, you should use the
   official way to do it (not implemented yet :)
*/
#define _h2py(x) (x._o)
#define _py2h(o) ((HPy){o})


#define HPy_NULL ((HPy){NULL})
#define HPy_IsNull(x) ((x)._o == NULL)

HPyAPI_FUNC(HPy)
HPyNone_Get(HPyContext ctx)
{
    Py_INCREF(Py_None);
    return _py2h(Py_None);
}

HPyAPI_FUNC(HPy)
HPy_Dup(HPyContext ctx, HPy handle)
{
    Py_XINCREF(_h2py(handle));
    return handle;
}

HPyAPI_FUNC(void)
HPy_Close(HPyContext ctx, HPy handle)
{
    Py_XDECREF(_h2py(handle));
}

/* moduleobject.h */
typedef PyModuleDef HPyModuleDef;
#define HPyModuleDef_HEAD_INIT PyModuleDef_HEAD_INIT

HPyAPI_FUNC(HPy)
HPyModule_Create(HPyContext ctx, HPyModuleDef *mdef) {
    return _py2h(PyModule_Create(mdef));
}

#define HPy_MODINIT(modname)                                   \
    static HPy init_##modname##_impl(HPyContext ctx);          \
    PyMODINIT_FUNC                                             \
    PyInit_##modname(void)                                     \
    {                                                          \
        return _h2py(init_##modname##_impl(_HPyGetContext())); \
    }

/* methodobject.h */
typedef PyMethodDef HPyMethodDef;


/* function declaration */

#define HPy_FUNCTION(NAME)                                              \
    static HPy NAME##_impl(HPyContext, HPy, HPy);                       \
    static PyObject* NAME(PyObject *self, PyObject *args)               \
    {                                                                   \
        return _h2py(NAME##_impl(_HPyGetContext(), _py2h(self), _py2h(args)));\
    }


HPyAPI_FUNC(int)
HPyArg_ParseTuple(HPyContext ctx, HPy args, const char *fmt, ...)
{
    va_list vl;
    va_start(vl, fmt);
    int res = PyArg_VaParse(_h2py(args), fmt, vl);
    va_end(vl);
    /* XXX incref all returned 'PyObject*' */
    return res;
}


HPyAPI_FUNC(HPy)
HPyLong_FromLong(HPyContext ctx, long v)
{
    return _py2h(PyLong_FromLong(v));
}

HPyAPI_FUNC(HPy)
HPyNumber_Add(HPyContext ctx, HPy x, HPy y)
{
    return _py2h(PyNumber_Add(_h2py(x), _h2py(y)));
}

HPyAPI_FUNC(HPy)
HPyUnicode_FromString(HPyContext ctx, const char *utf8)
{
    return _py2h(PyUnicode_FromString(utf8));
}

HPyAPI_FUNC(HPy)
HPy_FromPyObject(HPyContext ctx, PyObject *obj)
{
    Py_XINCREF(obj);
    return _py2h(obj);
}

HPyAPI_FUNC(PyObject *)
HPy_AsPyObject(HPyContext ctx, HPy h)
{
    PyObject *result = _h2py(h);
    Py_XINCREF(result);
    return result;
}


#endif /* !HPy_CPYTHON_H */
