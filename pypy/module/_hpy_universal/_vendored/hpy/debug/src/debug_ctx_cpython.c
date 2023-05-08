/* =========== CPython-ONLY ===========
   In the following code, we use _py2h and _h2py and we assumed they are the
   ones defined by CPython's version of hpy.universal.

   DO NOT COMPILE THIS FILE UNLESS YOU ARE BUILDING CPython's hpy.universal.

   If you want to compile the debug mode into your own non-CPython version of
   hpy.universal, you should include debug_ctx_not_cpython.c.
   ====================================

   In theory, the debug mode is completely generic and can wrap a generic
   uctx. However, CPython is special because it does not have native support
   for HPy, so uctx contains the logic to call HPy functions from CPython, by
   using _HPy_CallRealFunctionFromTrampoline.

   uctx->ctx_CallRealFunctionFromTrampoline converts PyObject* into UHPy. So
   for the debug mode we need to:

       1. convert the PyObject* args into UHPys.
       2. wrap the UHPys into DHPys.
       3. unwrap the resulting DHPy and convert to PyObject*.
*/

#include <Python.h>
#include "debug_internal.h"
#include "hpy/runtime/ctx_type.h" // for call_traverseproc_from_trampoline
#include "hpy/runtime/ctx_module.h"
#include "handles.h" // for _py2h and _h2py

#if defined(_MSC_VER)
# include <malloc.h>   /* for alloca() */
#endif

static inline DHPy _py2dh(HPyContext *dctx, PyObject *obj)
{
    return DHPy_open(dctx, _py2h(obj));
}

static inline PyObject *_dh2py(HPyContext *dctx, DHPy dh)
{
    return _h2py(DHPy_unwrap(dctx, dh));
}

static void _buffer_h2py(HPyContext *dctx, const HPy_buffer *src, Py_buffer *dest)
{
    dest->buf = src->buf;
    dest->obj = HPy_AsPyObject(dctx, src->obj);
    dest->len = src->len;
    dest->itemsize = src->itemsize;
    dest->readonly = src->readonly;
    dest->ndim = src->ndim;
    dest->format = src->format;
    dest->shape = src->shape;
    dest->strides = src->strides;
    dest->suboffsets = src->suboffsets;
    dest->internal = src->internal;
}

static void _buffer_py2h(HPyContext *dctx, const Py_buffer *src, HPy_buffer *dest)
{
    dest->buf = src->buf;
    dest->obj = HPy_FromPyObject(dctx, src->obj);
    dest->len = src->len;
    dest->itemsize = src->itemsize;
    dest->readonly = src->readonly;
    dest->ndim = src->ndim;
    dest->format = src->format;
    dest->shape = src->shape;
    dest->strides = src->strides;
    dest->suboffsets = src->suboffsets;
    dest->internal = src->internal;
}

static HPyContext* _switch_to_next_dctx_from_cache(HPyContext *current_dctx) {
    HPyContext *next_dctx = hpy_debug_get_next_dctx_from_cache(current_dctx);
    if (next_dctx == NULL) {
        HPyErr_NoMemory(current_dctx);
        get_ctx_info(current_dctx)->is_valid = false;
        get_ctx_info(next_dctx)->is_valid = true;
        return NULL;
    }
    get_ctx_info(current_dctx)->is_valid = false;
    get_ctx_info(next_dctx)->is_valid = true;
    return next_dctx;
}

static void _switch_back_to_original_dctx(HPyContext *original_dctx, HPyContext *next_dctx) {
    get_ctx_info(next_dctx)->is_valid = false;
    get_ctx_info(original_dctx)->is_valid = true;
}

void debug_ctx_CallRealFunctionFromTrampoline(HPyContext *dctx,
                                              HPyFunc_Signature sig,
                                              void *func, void *args)
{
    switch (sig) {
    case HPyFunc_VARARGS: {
        HPyFunc_varargs f = (HPyFunc_varargs)func;
        _HPyFunc_args_VARARGS *a = (_HPyFunc_args_VARARGS*)args;
        DHPy dh_self = _py2dh(dctx, a->self);
        DHPy *dh_args = (DHPy *)alloca(a->nargs * sizeof(DHPy));
        for (HPy_ssize_t i = 0; i < a->nargs; i++) {
            dh_args[i] = _py2dh(dctx, a->args[i]);
        }

        HPyContext *next_dctx = _switch_to_next_dctx_from_cache(dctx);
        if (next_dctx == NULL) {
            a->result = NULL;
            return;
        }

        DHPy dh_result = f(next_dctx, dh_self, dh_args, a->nargs);

        _switch_back_to_original_dctx(dctx, next_dctx);

        DHPy_close_and_check(dctx, dh_self);
        for (HPy_ssize_t i = 0; i < a->nargs; i++) {
            DHPy_close_and_check(dctx, dh_args[i]);
        }
        a->result = _dh2py(dctx, dh_result);
        DHPy_close(dctx, dh_result);
        return;
    }
    case HPyFunc_KEYWORDS: {
        HPyFunc_keywords f = (HPyFunc_keywords)func;
        _HPyFunc_args_KEYWORDS *a = (_HPyFunc_args_KEYWORDS*)args;
        DHPy dh_self = _py2dh(dctx, a->self);
        size_t n_kwnames = a->kwnames != NULL ? PyTuple_GET_SIZE(a->kwnames) : 0;
        size_t nargs = PyVectorcall_NARGS(a->nargsf);
        size_t nargs_with_kw = nargs + n_kwnames;
        DHPy *dh_args = (DHPy *)alloca(nargs_with_kw * sizeof(DHPy));
        for (size_t i = 0; i < nargs_with_kw; i++) {
            dh_args[i] = _py2dh(dctx, a->args[i]);
        }
        DHPy dh_kwnames = _py2dh(dctx, a->kwnames);

        HPyContext *next_dctx = _switch_to_next_dctx_from_cache(dctx);
        if (next_dctx == NULL) {
            a->result = NULL;
            return;
        }

        DHPy dh_result = f(next_dctx, dh_self, dh_args, nargs, dh_kwnames);

        _switch_back_to_original_dctx(dctx, next_dctx);

        DHPy_close_and_check(dctx, dh_self);
        for (size_t i = 0; i < nargs_with_kw; i++) {
            DHPy_close_and_check(dctx, dh_args[i]);
        }
        DHPy_close_and_check(dctx, dh_kwnames);
        a->result = _dh2py(dctx, dh_result);
        DHPy_close(dctx, dh_result);
        return;
    }
    case HPyFunc_INITPROC: {
        HPyFunc_initproc f = (HPyFunc_initproc)func;
        _HPyFunc_args_INITPROC *a = (_HPyFunc_args_INITPROC*)args;
        DHPy dh_self = _py2dh(dctx, a->self);
        Py_ssize_t nargs = PyTuple_GET_SIZE(a->args);
        DHPy *dh_args = (DHPy *)alloca(nargs * sizeof(DHPy));
        for (Py_ssize_t i = 0; i < nargs; i++) {
            dh_args[i] = _py2dh(dctx, PyTuple_GET_ITEM(a->args, i));
        }
        DHPy dh_kw = _py2dh(dctx, a->kw);

        HPyContext *next_dctx = _switch_to_next_dctx_from_cache(dctx);
        if (next_dctx == NULL) {
            a->result = -1;
            return;
        }

        a->result = f(next_dctx, dh_self, dh_args, nargs, dh_kw);

        _switch_back_to_original_dctx(dctx, next_dctx);

        DHPy_close_and_check(dctx, dh_self);
        for (Py_ssize_t i = 0; i < nargs; i++) {
            DHPy_close_and_check(dctx, dh_args[i]);
        }
        DHPy_close_and_check(dctx, dh_kw);
        return;
    }
    case HPyFunc_NEWFUNC: {
        HPyFunc_newfunc f = (HPyFunc_newfunc)func;
        _HPyFunc_args_NEWFUNC *a = (_HPyFunc_args_NEWFUNC*)args;
        DHPy dh_self = _py2dh(dctx, a->self);
        Py_ssize_t nargs = PyTuple_GET_SIZE(a->args);
        DHPy *dh_args = (DHPy *)alloca(nargs * sizeof(DHPy));
        for (Py_ssize_t i = 0; i < nargs; i++) {
            dh_args[i] = _py2dh(dctx, PyTuple_GET_ITEM(a->args, i));
        }
        DHPy dh_kw = _py2dh(dctx, a->kw);

        HPyContext *next_dctx = _switch_to_next_dctx_from_cache(dctx);
        if (next_dctx == NULL) {
            a->result = NULL;
            return;
        }

        DHPy dh_result = f(next_dctx, dh_self, dh_args, nargs, dh_kw);

        _switch_back_to_original_dctx(dctx, next_dctx);

        DHPy_close_and_check(dctx, dh_self);
        for (Py_ssize_t i = 0; i < nargs; i++) {
            DHPy_close_and_check(dctx, dh_args[i]);
        }
        DHPy_close_and_check(dctx, dh_kw);
        a->result = _dh2py(dctx, dh_result);
        DHPy_close(dctx, dh_result);
        return;
    }
    case HPyFunc_GETBUFFERPROC: {
        HPyFunc_getbufferproc f = (HPyFunc_getbufferproc)func;
        _HPyFunc_args_GETBUFFERPROC *a = (_HPyFunc_args_GETBUFFERPROC*)args;
        HPy_buffer hbuf;
        DHPy dh_self = _py2dh(dctx, a->self);

        HPyContext *next_dctx = _switch_to_next_dctx_from_cache(dctx);
        if (next_dctx == NULL) {
            a->result = -1;
            return;
        }

        a->result = f(next_dctx, dh_self, &hbuf, a->flags);

        _switch_back_to_original_dctx(dctx, next_dctx);

        DHPy_close_and_check(dctx, dh_self);
        if (a->result < 0) {
            a->view->obj = NULL;
            return;
        }
        _buffer_h2py(dctx, &hbuf, a->view);
        HPy_Close(dctx, hbuf.obj);
        return;
    }
    case HPyFunc_RELEASEBUFFERPROC: {
        HPyFunc_releasebufferproc f = (HPyFunc_releasebufferproc)func;
        _HPyFunc_args_RELEASEBUFFERPROC *a = (_HPyFunc_args_RELEASEBUFFERPROC*)args;
        HPy_buffer hbuf;
        _buffer_py2h(dctx, a->view, &hbuf);
        DHPy dh_self = _py2dh(dctx, a->self);

        HPyContext *next_dctx = _switch_to_next_dctx_from_cache(dctx);
        if (next_dctx == NULL) {
            return;
        }

        f(next_dctx, dh_self, &hbuf);

        _switch_back_to_original_dctx(dctx, next_dctx);

        DHPy_close_and_check(dctx, dh_self);
        // XXX: copy back from hbuf?
        HPy_Close(dctx, hbuf.obj);
        return;
    }
    case HPyFunc_TRAVERSEPROC: {
        HPyFunc_traverseproc f = (HPyFunc_traverseproc)func;
        _HPyFunc_args_TRAVERSEPROC *a = (_HPyFunc_args_TRAVERSEPROC*)args;

        HPyContext *next_dctx = _switch_to_next_dctx_from_cache(dctx);
        if (next_dctx == NULL) {
            a->result = -1;
            return;
        }

        a->result = call_traverseproc_from_trampoline(f, a->self,
                                                      a->visit, a->arg);

        _switch_back_to_original_dctx(dctx, next_dctx);
        return;
    }
    case HPyFunc_CAPSULE_DESTRUCTOR: {
        HPyFunc_Capsule_Destructor f = (HPyFunc_Capsule_Destructor)func;
        PyObject *capsule = (PyObject *)args;
        const char *name = PyCapsule_GetName(capsule);
        f(name, PyCapsule_GetPointer(capsule, name),
                PyCapsule_GetContext(capsule));
        return;
    }
    case HPyFunc_MOD_CREATE: {
        HPyFunc_unaryfunc f = (HPyFunc_unaryfunc)func;
        _HPyFunc_args_UNARYFUNC *a = (_HPyFunc_args_UNARYFUNC*)args;
        DHPy dh_arg0 = _py2dh(dctx, a->arg0);
        DHPy dh_result = f(dctx, dh_arg0);
        DHPy_close_and_check(dctx, dh_arg0);
        a->result = _dh2py(dctx, dh_result);
        _HPyModule_CheckCreateSlotResult(&a->result);
        DHPy_close(dctx, dh_result);
        return;
    }
#include "autogen_debug_ctx_call.i"
    default:
        Py_FatalError("Unsupported HPyFunc_Signature in debug_ctx_cpython.c");
    }
}
