from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, cpython_struct
from pypy.interpreter.module import Module

PyMethodDef = cpython_struct('PyMethodDef')

def PyImport_AddModule(space, name):
    w_name = space.wrap(name)
    w_mod = space.wrap(Module(space, w_name))

    w_modules = space.sys.get('modules')
    space.setitem(w_modules, w_name, w_mod)
    return w_mod

@cpython_api([rffi.CCHARP, lltype.Ptr(PyMethodDef)], lltype.Void)
def Py_InitModule(space, name, methods):
    name = rffi.charp2str(name)
    PyImport_AddModule(space, name)
    assert not methods # For the moment
