#ifndef HPY_CPYTHON_HPYFUNC_TRAMPOLINES_H
#define HPY_CPYTHON_HPYFUNC_TRAMPOLINES_H

typedef HPy (*_HPyCFunction_VARARGS)(HPyContext*, HPy, const HPy *, size_t);
#define _HPyFunc_TRAMPOLINE_HPyFunc_VARARGS(SYM, IMPL)                  \
    static PyObject*                                                    \
    SYM(PyObject *self, PyObject *const *args, Py_ssize_t nargs)        \
    {                                                                   \
        _HPyCFunction_VARARGS func = (_HPyCFunction_VARARGS)IMPL;       \
        return _h2py(func(_HPyGetContext(),                             \
                              _py2h(self), _arr_py2h(args), nargs));    \
    }

typedef HPy (*_HPyCFunction_KEYWORDS)(HPyContext*, HPy, const HPy *, size_t, HPy);
#define _HPyFunc_TRAMPOLINE_HPyFunc_KEYWORDS(SYM, IMPL)                   \
    static PyObject *                                                     \
    SYM(PyObject *self, PyObject *const *args, size_t nargsf,             \
            PyObject *kwnames)                                            \
    {                                                                     \
        _HPyCFunction_KEYWORDS func = (_HPyCFunction_KEYWORDS)IMPL;       \
        /* We also use HPyFunc_KEYWORDS for HPy_tp_call which is */       \
        /* called via vectorcall and so nargsf may have the flag set */   \
        return _h2py(func(_HPyGetContext(), _py2h(self), _arr_py2h(args), \
                          PyVectorcall_NARGS(nargsf), _py2h(kwnames)));   \
    }

typedef int (*_HPyCFunction_INITPROC)(HPyContext*, HPy, const HPy *, HPy_ssize_t, HPy);
#define _HPyFunc_TRAMPOLINE_HPyFunc_INITPROC(SYM, IMPL)                 \
    static int                                                          \
    SYM(PyObject *self, PyObject *args, PyObject *kw)                   \
    {                                                                   \
        /* get the tuple elements as an array of "PyObject *", which */ \
        /* is equivalent to an array of "HPy" with enough casting... */ \
        PyObject *const *items = &PyTuple_GET_ITEM(args, 0);            \
        Py_ssize_t nargs = PyTuple_GET_SIZE(args);                      \
        _HPyCFunction_INITPROC func = (_HPyCFunction_INITPROC)IMPL; \
        return func(_HPyGetContext(), _py2h(self),                      \
                    _arr_py2h(items), nargs, _py2h(kw));                \
    }

typedef HPy (*_HPyCFunction_NEWFUNC)(HPyContext*, HPy, const HPy *, HPy_ssize_t, HPy);
#define _HPyFunc_TRAMPOLINE_HPyFunc_NEWFUNC(SYM, IMPL)                  \
    static PyObject *                                                   \
    SYM(PyObject *self, PyObject *args, PyObject *kw)                   \
    {                                                                   \
        /* get the tuple elements as an array of "PyObject *", which */ \
        /* is equivalent to an array of "HPy" with enough casting... */ \
        PyObject *const *items = &PyTuple_GET_ITEM(args, 0);            \
        Py_ssize_t nargs = PyTuple_GET_SIZE(args);                      \
        _HPyCFunction_NEWFUNC func = (_HPyCFunction_NEWFUNC)IMPL;       \
        return _h2py(func(_HPyGetContext(), _py2h(self),                \
                         _arr_py2h(items), nargs, _py2h(kw)));          \
    }

/* special case: the HPy_tp_destroy slot doesn't map to any CPython slot.
   Instead, it is called from our own tp_dealloc: see also
   hpytype_dealloc(). */
#define _HPyFunc_TRAMPOLINE_HPyFunc_DESTROYFUNC(SYM, IMPL)              \
    static void SYM(void) { abort(); }

/* this needs to be written manually because HPy has a different type for
   "op": HPy_RichCmpOp instead of int */
typedef HPy (*_HPyCFunction_RICHCMPFUNC)(HPyContext *, HPy, HPy, int);
#define _HPyFunc_TRAMPOLINE_HPyFunc_RICHCMPFUNC(SYM, IMPL)                 \
    static cpy_PyObject *                                                  \
    SYM(PyObject *self, PyObject *obj, int op)                             \
    {                                                                      \
        _HPyCFunction_RICHCMPFUNC func = (_HPyCFunction_RICHCMPFUNC)IMPL;  \
        return _h2py(func(_HPyGetContext(), _py2h(self), _py2h(obj), op)); \
    }

/* With the cpython ABI, Py_buffer and HPy_buffer are ABI-compatible.
 * Even though casting between them is technically undefined behavior, it
 * should always work. That way, we avoid a costly allocation and copy. */
typedef int (*_HPyCFunction_GETBUFFERPROC)(HPyContext *, HPy, HPy_buffer *, int);
#define _HPyFunc_TRAMPOLINE_HPyFunc_GETBUFFERPROC(SYM, IMPL) \
    static int SYM(PyObject *arg0, Py_buffer *arg1, int arg2) \
    { \
        _HPyCFunction_GETBUFFERPROC func = (_HPyCFunction_GETBUFFERPROC)IMPL;  \
        return (func(_HPyGetContext(), _py2h(arg0), (HPy_buffer*)arg1, arg2)); \
    }

typedef int (*_HPyCFunction_RELEASEBUFFERPROC)(HPyContext *, HPy, HPy_buffer *);
#define _HPyFunc_TRAMPOLINE_HPyFunc_RELEASEBUFFERPROC(SYM, IMPL) \
    static void SYM(PyObject *arg0, Py_buffer *arg1) \
    { \
        _HPyCFunction_RELEASEBUFFERPROC func = (_HPyCFunction_RELEASEBUFFERPROC)IMPL; \
        func(_HPyGetContext(), _py2h(arg0), (HPy_buffer*)arg1); \
        return; \
    }


#define _HPyFunc_TRAMPOLINE_HPyFunc_TRAVERSEPROC(SYM, IMPL)             \
    static int SYM(cpy_PyObject *self, cpy_visitproc visit, void *arg)  \
    {                                                                   \
        return call_traverseproc_from_trampoline((HPyFunc_traverseproc)IMPL, self,            \
                                                 visit, arg);           \
    }

#define HPyCapsule_DESTRUCTOR_TRAMPOLINE(SYM, IMPL)                            \
    static void SYM(PyObject *capsule)                                         \
    {                                                                          \
        const char *name = PyCapsule_GetName(capsule);                         \
        IMPL(name, PyCapsule_GetPointer(capsule, name),                        \
                PyCapsule_GetContext(capsule));                                \
    }

extern void
_HPyModule_CheckCreateSlotResult(cpy_PyObject **result);

#define _HPyFunc_TRAMPOLINE_HPyFunc_MOD_CREATE(SYM, IMPL)                      \
    static cpy_PyObject* SYM(cpy_PyObject *spec, cpy_PyModuleDef *def)         \
    {                                                                          \
        (void) def; /* avoid 'unused' warning */                               \
        cpy_PyObject* result = _h2py(IMPL(_HPyGetContext(), _py2h(spec)));     \
        _HPyModule_CheckCreateSlotResult(&result);                             \
        return result;                                                         \
    }

#endif // HPY_CPYTHON_HPYFUNC_TRAMPOLINES_H
