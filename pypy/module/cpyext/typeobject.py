from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, cpython_struct, PyObject
from pypy.interpreter.module import Module
from pypy.module.cpyext.methodobject import PyCFunction_NewEx

PyCFunction = lltype.Ptr(lltype.FuncType([PyObject, PyObject], PyObject))

PyTypeObject = cpython_struct(
        "PyTypeObject",
        [])
PyTypeObjectPtr = lltype.Ptr(PyTypeObject)

def PyImport_AddModule(space, name):
    w_name = space.wrap(name)
    w_mod = space.wrap(Module(space, w_name))

    w_modules = space.sys.get('modules')
    space.setitem(w_modules, w_name, w_mod)
    return w_mod

#@cpython_api([rffi.CCHARP, lltype.Ptr(PyMethodDef)], lltype.Void)
def Py_InitModule(space, name, methods):
    modname = rffi.charp2str(name)
    w_mod = PyImport_AddModule(space, modname)
    methods = rffi.cast(rffi.CArrayPtr(PyMethodDef), methods)
    if methods:
        i = 0
        while True:
            method = methods[i]
            if not method.c_ml_name: break

            methodname = rffi.charp2str(method.c_ml_name)
            flags = method.c_ml_flags
            w_function = PyCFunction_NewEx(space, method, None, modname)
            space.setattr(w_mod,
                          space.wrap(methodname),
                          w_function)
            i = i + 1
