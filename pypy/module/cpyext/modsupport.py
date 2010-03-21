from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, cpython_struct, PyObject
from pypy.interpreter.module import Module
from pypy.module.cpyext.methodobject import PyCFunction_NewEx
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall

PyCFunction = lltype.Ptr(lltype.FuncType([PyObject, PyObject], PyObject))

PyMethodDef = cpython_struct(
    'PyMethodDef',
    [('ml_name', rffi.CCHARP),
     ('ml_meth', PyCFunction),
     ('ml_flags', rffi.INT),
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
    dict_w = convert_method_defs(space, methods)
    for w_key, w_value in dict_w.items():
        space.setattr(w_mod, w_key, w_value)
    return w_mod


def convert_method_defs(space, methods):
    methods = rffi.cast(rffi.CArrayPtr(PyMethodDef), methods)
    dict_w = {}
    if methods:
        i = 0
        while True:
            method = methods[i]
            if not method.c_ml_name: break

            methodname = rffi.charp2str(method.c_ml_name)
            flags = method.c_ml_flags
            w_function = PyCFunction_NewEx(space, method, None)
            dict_w[space.wrap(methodname)] = w_function
            i = i + 1
    return dict_w


@cpython_api([PyObject], rffi.INT)
def PyModule_Check(space, w_obj):
    w_type = space.gettypeobject(Module.typedef)
    w_obj_type = space.type(w_obj)
    return space.is_w(w_obj_type, w_type) or space.is_true(space.issubtype(w_obj_type, w_type))

@cpython_api([PyObject], PyObject)
def PyModule_GetDict(space, w_mod):
    if PyModule_Check(space, w_mod):
        assert isinstance(w_mod, Module)
        return w_mod.getdict()
    else:
        PyErr_BadInternalCall()
