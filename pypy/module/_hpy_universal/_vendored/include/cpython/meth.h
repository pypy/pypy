#ifndef HPY_CPYTHON_METH_H
#define HPY_CPYTHON_METH_H

typedef PyMethodDef HPyMethodDef;

// this is the type of the field HPyMethodDef.ml_meth: cast to it to silence
// warnings
typedef PyCFunction HPyMeth;

// XXX: we need to find a way to let the user declare things as static if
// he/she wants

/* METH declaration */
#define HPy_DECL_METH_NOARGS(NAME) PyObject* NAME(PyObject *, PyObject *);
#define HPy_DECL_METH_O(NAME) HPy_DECL_METH_NOARGS(NAME)
#define HPy_DECL_METH_VARARGS(NAME) HPy_DECL_METH_NOARGS(NAME)
#define HPy_DECL_METH_KEYWORDS(NAME) PyObject* NAME(PyObject *, PyObject *, PyObject *);

/* METH definition */
#define HPy_DEF_METH_NOARGS(NAME)                                       \
    static HPy NAME##_impl(HPyContext, HPy);                            \
    PyObject* NAME(PyObject *self, PyObject *noargs)                    \
    {                                                                   \
        return _h2py(NAME##_impl(_HPyGetContext(), _py2h(self)));       \
    }

#define HPy_DEF_METH_O(NAME)                                            \
    static HPy NAME##_impl(HPyContext, HPy, HPy);                       \
    PyObject* NAME(PyObject *self, PyObject *arg)                       \
    {                                                                   \
        return _h2py(NAME##_impl(_HPyGetContext(), _py2h(self), _py2h(arg)));\
    }

#define HPy_DEF_METH_VARARGS(NAME)                                             \
    static HPy NAME##_impl(HPyContext ctx, HPy self,                           \
                           HPy *args, Py_ssize_t nargs);                       \
    PyObject* NAME(PyObject *self, PyObject *args)                             \
    {                                                                          \
        /* get the tuple elements as an array of "PyObject *", which */        \
        /* is equivalent to an array of "HPy" with enough casting... */        \
        HPy *items = (HPy *)&PyTuple_GET_ITEM(args, 0);                        \
        Py_ssize_t nargs = PyTuple_GET_SIZE(args);                             \
        return _h2py(NAME##_impl(_HPyGetContext(), _py2h(self), items, nargs));\
    }

#define HPy_DEF_METH_KEYWORDS(NAME)                                            \
    static HPy NAME##_impl(HPyContext ctx, HPy self,                           \
                           HPy *args, HPy_ssize_t nargs, HPy kw);              \
    PyObject* NAME(PyObject *self, PyObject *args, PyObject *kw)               \
    {                                                                          \
        /* get the tuple elements as an array of "PyObject *", which */        \
        /* is equivalent to an array of "HPy" with enough casting... */        \
        HPy *items = (HPy *)&PyTuple_GET_ITEM(args, 0);                        \
        Py_ssize_t nargs = PyTuple_GET_SIZE(args);                             \
        return _h2py(NAME##_impl(_HPyGetContext(), _py2h(self),                \
                     items, nargs, _py2h(kw)));                                \
    }

#define HPy_METH_NOARGS METH_NOARGS
#define HPy_METH_O METH_O
#define HPy_METH_VARARGS METH_VARARGS
#define HPy_METH_KEYWORDS (METH_VARARGS | METH_KEYWORDS)


#endif // HPY_CPYTHON_METH_H
