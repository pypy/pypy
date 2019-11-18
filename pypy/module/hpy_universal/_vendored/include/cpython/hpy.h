#ifndef HPy_CPYTHON_H
#define HPy_CPYTHON_H




/* XXX: it would be nice if we could include hpy.h WITHOUT bringing in all the
   stuff from Python.h, to make sure that people don't use the CPython API by
   mistake. How to achieve it, though? Is defining Py_LIMITED_API enough? */

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
typedef Py_ssize_t HPy_ssize_t;

/* For internal usage only. These should be #undef at the end of this header.
   If you need to convert HPy to PyObject* and vice-versa, you should use the
   official way to do it (not implemented yet :)
*/
#define _h2py(x) (x._o)
#define _py2h(o) ((HPy){o})

typedef struct _HPyContext_s {
    HPy h_None;
    HPy h_True;
    HPy h_False;
    HPy h_ValueError;
} *HPyContext;

/* XXX! should be defined only once, not once for every .c! */
static struct _HPyContext_s _global_ctx;

#define HPy_NULL ((HPy){NULL})
#define HPy_IsNull(x) ((x)._o == NULL)

HPyAPI_FUNC(HPyContext)
_HPyGetContext(void) {
    HPyContext ctx = &_global_ctx;
    if (HPy_IsNull(ctx->h_None)) {
        // XXX: we need to find a better way to check whether the ctx is
        // initialized or not
        ctx->h_None = _py2h(Py_None);
        ctx->h_True = _py2h(Py_True);
        ctx->h_False = _py2h(Py_False);
        ctx->h_ValueError = _py2h(PyExc_ValueError);
    }
    return ctx;
}



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

#define HPy_METH_NOARGS(NAME)                                           \
    static HPy NAME##_impl(HPyContext, HPy);                            \
    static PyObject* NAME(PyObject *self, PyObject *noargs)             \
    {                                                                   \
        return _h2py(NAME##_impl(_HPyGetContext(), _py2h(self)));       \
    }

#define HPy_METH_O(NAME)                                                \
    static HPy NAME##_impl(HPyContext, HPy, HPy);                       \
    static PyObject* NAME(PyObject *self, PyObject *arg)                \
    {                                                                   \
        return _h2py(NAME##_impl(_HPyGetContext(), _py2h(self), _py2h(arg)));\
    }

#define HPy_METH_VARARGS(NAME)                                          \
    static HPy NAME##_impl(HPyContext, HPy, HPy *, Py_ssize_t);         \
    static PyObject* NAME(PyObject *self, PyObject *args)               \
    {                                                                   \
        /* get the tuple elements as an array of "PyObject *", which */ \
        /* is equivalent to an array of "HPy" with enough casting... */ \
        HPy *items = (HPy *)&PyTuple_GET_ITEM(args, 0);                 \
        Py_ssize_t nargs = PyTuple_GET_SIZE(args);                      \
        return _h2py(NAME##_impl(_HPyGetContext(), _py2h(self), items, nargs));\
    }


HPyAPI_FUNC(int)
HPyArg_Parse(HPyContext ctx, HPy *args, Py_ssize_t nargs, const char *fmt, ...)
{
    va_list vl;
    va_start(vl, fmt);
    const char *fmt1 = fmt;
    Py_ssize_t i = 0;

    while (*fmt1 != 0) {
        if (i >= nargs) {
            abort(); // XXX
        }
        switch (*fmt1++) {
        case 'l': {
            long *output = va_arg(vl, long *);
            long value = PyLong_AsLong(_h2py(args[i]));
            // XXX check for exceptions
            *output = value;
            break;
        }
        default:
            abort();  // XXX
        }
        i++;
    }
    if (i != nargs) {
        abort();   // XXX
    }

    va_end(vl);
    return 1;
}


HPyAPI_FUNC(HPy)
HPyLong_FromLong(HPyContext ctx, long v)
{
    return _py2h(PyLong_FromLong(v));
}

HPyAPI_FUNC(long)
HPyLong_AsLong(HPyContext ctx, HPy h)
{
    return PyLong_AsLong(_h2py(h));
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

HPyAPI_FUNC(void)
HPyErr_SetString(HPyContext ctx, HPy type, const char *message)
{
    PyErr_SetString(_h2py(type), message);
}


#endif /* !HPy_CPYTHON_H */
