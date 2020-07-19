#ifndef HPY_CPYTHON_HPYFUNC_TRAMPOLINES_H
#define HPY_CPYTHON_HPYFUNC_TRAMPOLINES_H


#define _HPyFunc_TRAMPOLINE_HPyFunc_NOARGS(SYM, IMPL)                   \
    static PyObject *                                                   \
    SYM(PyObject *self, PyObject *noargs)                               \
    {                                                                   \
        return _h2py(IMPL(_HPyGetContext(), _py2h(self)));              \
    }

#define _HPyFunc_TRAMPOLINE_HPyFunc_O(SYM, IMPL)                        \
    static PyObject *                                                   \
    SYM(PyObject *self, PyObject *arg)                                  \
    {                                                                   \
        return _h2py(IMPL(_HPyGetContext(), _py2h(self), _py2h(arg)));  \
    }

#define _HPyFunc_TRAMPOLINE_HPyFunc_VARARGS(SYM, IMPL)                  \
    static PyObject*                                                    \
    SYM(PyObject *self, PyObject *args)                                 \
    {                                                                   \
        /* get the tuple elements as an array of "PyObject *", which */ \
        /* is equivalent to an array of "HPy" with enough casting... */ \
        HPy *items = (HPy *)&PyTuple_GET_ITEM(args, 0);                 \
        Py_ssize_t nargs = PyTuple_GET_SIZE(args);                      \
        return _h2py(IMPL(_HPyGetContext(),                             \
                                 _py2h(self), items, nargs));           \
    }

#define _HPyFunc_TRAMPOLINE_HPyFunc_KEYWORDS(SYM, IMPL)                 \
    static PyObject *                                                   \
    SYM(PyObject *self, PyObject *args, PyObject *kw)                   \
    {                                                                   \
        /* get the tuple elements as an array of "PyObject *", which */ \
        /* is equivalent to an array of "HPy" with enough casting... */ \
        HPy *items = (HPy *)&PyTuple_GET_ITEM(args, 0);                 \
        Py_ssize_t nargs = PyTuple_GET_SIZE(args);                      \
        return _h2py(IMPL(_HPyGetContext(), _py2h(self),                \
                                 items, nargs, _py2h(kw)));             \
    }

#endif // HPY_CPYTHON_HPYFUNC_TRAMPOLINES_H
