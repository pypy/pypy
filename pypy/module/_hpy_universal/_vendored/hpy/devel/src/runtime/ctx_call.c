#include <Python.h>
#include "hpy.h"
#if defined(_MSC_VER)
# include <malloc.h>   /* for alloca() */
#endif

#ifndef HPY_ABI_CPYTHON
   // for _h2py and _py2h
#  include "handles.h"
#endif

_HPy_HIDDEN HPy
ctx_CallTupleDict(HPyContext *ctx, HPy callable, HPy args, HPy kw)
{
    PyObject *obj;
    if (!HPy_IsNull(args) && !HPyTuple_Check(ctx, args)) {
       HPyErr_SetString(ctx, ctx->h_TypeError,
           "HPy_CallTupleDict requires args to be a tuple or null handle");
       return HPy_NULL;
    }
    if (!HPy_IsNull(kw) && !HPyDict_Check(ctx, kw)) {
       HPyErr_SetString(ctx, ctx->h_TypeError,
           "HPy_CallTupleDict requires kw to be a dict or null handle");
       return HPy_NULL;
    }
    if (HPy_IsNull(kw)) {
        obj = PyObject_CallObject(_h2py(callable), _h2py(args));
    }
    else if (!HPy_IsNull(args)){
        obj = PyObject_Call(_h2py(callable), _h2py(args), _h2py(kw));
    }
    else {
        // args is null, but kw is not, so we need to create an empty args tuple
        // for CPython's PyObject_Call
        HPy *items = NULL;
        HPy empty_tuple = HPyTuple_FromArray(ctx, items, 0);
        obj = PyObject_Call(_h2py(callable), _h2py(empty_tuple), _h2py(kw));
        HPy_Close(ctx, empty_tuple);
    }
    return _py2h(obj);
}

#if PY_VERSION_HEX < 0x03090000
#    define PyObject_Vectorcall _PyObject_Vectorcall
#endif

_HPy_HIDDEN HPy
ctx_Call(HPyContext *ctx, HPy h_callable, const HPy *h_args, size_t nargs, HPy h_kwnames)
{
    PyObject *kwnames;
    size_t n_all_args;

    if (HPy_IsNull(h_kwnames)) {
        kwnames = NULL;
        n_all_args = nargs;
    } else {
        kwnames = _h2py(h_kwnames);
        assert(kwnames != NULL);
        assert(PyTuple_Check(kwnames));
        n_all_args = nargs + PyTuple_GET_SIZE(kwnames);
        assert(n_all_args >= nargs);
    }

    /* Since we already allocate a fresh args array, we make it one element
       larger and set PY_VECTORCALL_ARGUMENTS_OFFSET to avoid further
       allocations from CPython. */
    PyObject **args = (PyObject **) alloca((n_all_args + 1) * sizeof(PyObject *));
    for (size_t i = 0; i < n_all_args; i++) {
        args[i+1] = _h2py(h_args[i]);
    }

    return _py2h(PyObject_Vectorcall(_h2py(h_callable), args+1,
            nargs | PY_VECTORCALL_ARGUMENTS_OFFSET, kwnames));
}

#if PY_VERSION_HEX < 0x03090000
#    undef PyObject_Vectorcall
#endif

_HPy_HIDDEN HPy
ctx_CallMethod(HPyContext *ctx, HPy h_name, const HPy *h_args, size_t nargs,
               HPy h_kwnames)
{
    PyObject *result, *kwnames;
    size_t n_all_args;

    if (HPy_IsNull(h_kwnames)) {
        kwnames = NULL;
        n_all_args = nargs;
    } else {
        kwnames = _h2py(h_kwnames);
        assert(kwnames != NULL);
        assert(PyTuple_Check(kwnames));
        n_all_args = nargs + PyTuple_GET_SIZE(kwnames);
        assert(n_all_args >= nargs);
    }

    /* Since we already allocate a fresh args array, we make it one element
       larger and set PY_VECTORCALL_ARGUMENTS_OFFSET to avoid further
       allocations from CPython. */
    PyObject **args = (PyObject **) alloca(
                          (n_all_args + 1) * sizeof(PyObject *));
    for (size_t i = 0; i < n_all_args; i++) {
        args[i+1] = _h2py(h_args[i]);
    }

#if PY_VERSION_HEX < 0x03090000
    PyObject *method = PyObject_GetAttr(args[1], _h2py(h_name));
    if (method == NULL)
        return HPy_NULL;
    result = _PyObject_Vectorcall(method, &args[2],
                 (nargs-1) | PY_VECTORCALL_ARGUMENTS_OFFSET, kwnames);
    Py_DECREF(method);
#else
    result = PyObject_VectorcallMethod(_h2py(h_name), args+1,
                 nargs | PY_VECTORCALL_ARGUMENTS_OFFSET, kwnames);
#endif
    return _py2h(result);
}
