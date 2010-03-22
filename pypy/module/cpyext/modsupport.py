from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, cpython_struct, PyObject, \
        METH_STATIC, METH_CLASS, METH_COEXIST, general_check
from pypy.interpreter.module import Module
from pypy.module.cpyext.methodobject import PyCFunction_NewEx, PyDescr_NewMethod
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall

PyCFunction = lltype.Ptr(lltype.FuncType([PyObject, PyObject], PyObject))

PyMethodDef = cpython_struct(
    'PyMethodDef',
    [('ml_name', rffi.CCHARP),
     ('ml_meth', PyCFunction),
     ('ml_flags', rffi.INT_real),
     ])

def PyImport_AddModule(space, name):
    w_name = space.wrap(name)
    w_mod = space.wrap(Module(space, w_name))

    w_modules = space.sys.get('modules')
    space.setitem(w_modules, w_name, w_mod)
    return w_mod

@cpython_api([rffi.CCHARP, lltype.Ptr(PyMethodDef)], PyObject, borrowed=True)
def Py_InitModule(space, name, methods):
    modname = rffi.charp2str(name)
    w_mod = PyImport_AddModule(space, modname)
    dict_w = {}
    convert_method_defs(space, dict_w, methods, None)
    for key, w_value in dict_w.items():
        space.setattr(w_mod, space.wrap(key), w_value)
    return w_mod


def convert_method_defs(space, dict_w, methods, pto):
    methods = rffi.cast(rffi.CArrayPtr(PyMethodDef), methods)
    if methods:
        i = -1
        while True:
            i = i + 1
            method = methods[i]
            if not method.c_ml_name: break

            methodname = rffi.charp2str(method.c_ml_name)
            flags = method.c_ml_flags
            if pto is None:
                if flags & METH_CLASS or flags & METH_STATIC:
                    raise OperationError(space.w_ValueError,
                            "module functions cannot set METH_CLASS or METH_STATIC")
                w_obj = PyCFunction_NewEx(space, method, None)
            else:
                if methodname in dict_w and not (flags & METH_COEXIST):
                    continue
                if flags & METH_CLASS:
                    if flags & METH_STATIC:
                        raise OperationError(space.w_ValueError,
                                "method cannot be both class and static")
                    w_obj = PyDescr_NewClassMethod(pto, method)
                elif flags & METH_STATIC:
                    w_func = PyCFunction_NewEx(space, method, None)
                    w_obj = PyStaticMethod_New(space, w_func)
                else:
                    w_obj = PyDescr_NewMethod(space, pto, method)
            dict_w[methodname] = w_obj


@cpython_api([PyObject], rffi.INT_real)
def PyModule_Check(space, w_obj):
    w_type = space.gettypeobject(Module.typedef)
    return general_check(space, w_obj, w_type)

@cpython_api([PyObject], PyObject)
def PyModule_GetDict(space, w_mod):
    if PyModule_Check(space, w_mod):
        assert isinstance(w_mod, Module)
        return w_mod.getdict()
    else:
        PyErr_BadInternalCall()
