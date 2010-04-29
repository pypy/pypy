from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, cpython_struct, \
        METH_STATIC, METH_CLASS, METH_COEXIST, CANNOT_FAIL, CONST_STRING
from pypy.module.cpyext.pyobject import PyObject, register_container
from pypy.interpreter.module import Module
from pypy.module.cpyext.methodobject import W_PyCFunctionObject, PyCFunction_NewEx, PyDescr_NewMethod, PyMethodDef, PyCFunction
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.interpreter.error import OperationError

def PyImport_AddModule(space, name):
    w_name = space.wrap(name)
    w_mod = space.wrap(Module(space, w_name))

    w_modules = space.sys.get('modules')
    space.setitem(w_modules, w_name, w_mod)
    return w_mod

@cpython_api([CONST_STRING, lltype.Ptr(PyMethodDef), CONST_STRING,
              PyObject, rffi.INT_real], PyObject, borrowed=False) # we cannot borrow here
def Py_InitModule4(space, name, methods, doc, w_self, apiver):
    from pypy.module.cpyext.typeobjectdefs import PyTypeObjectPtr
    modname = rffi.charp2str(name)
    w_mod = PyImport_AddModule(space, modname)
    dict_w = {}
    convert_method_defs(space, dict_w, methods, lltype.nullptr(PyTypeObjectPtr.TO), w_self)
    for key, w_value in dict_w.items():
        space.setattr(w_mod, space.wrap(key), w_value)
    if doc:
        space.setattr(w_mod, space.wrap("__doc__"),
                      space.wrap(rffi.charp2str(doc)))
    return w_mod


def convert_method_defs(space, dict_w, methods, pto, w_self=None):
    methods = rffi.cast(rffi.CArrayPtr(PyMethodDef), methods)
    if methods:
        i = -1
        while True:
            i = i + 1
            method = methods[i]
            if not method.c_ml_name: break

            methodname = rffi.charp2str(method.c_ml_name)
            flags = rffi.cast(lltype.Signed, method.c_ml_flags)
            if method.c_ml_doc:
                doc = rffi.charp2str(method.c_ml_doc)
            else:
                doc = None

            if not pto:
                if flags & METH_CLASS or flags & METH_STATIC:
                    raise OperationError(space.w_ValueError,
                            space.wrap("module functions cannot set METH_CLASS or METH_STATIC"))
                w_obj = space.wrap(W_PyCFunctionObject(space, method, w_self, doc))
            else:
                if methodname in dict_w and not (flags & METH_COEXIST):
                    continue
                if flags & METH_CLASS:
                    if flags & METH_STATIC:
                        raise OperationError(space.w_ValueError,
                                space.wrap("method cannot be both class and static"))
                    #w_obj = PyDescr_NewClassMethod(pto, method)
                    w_obj = space.w_Ellipsis # XXX
                elif flags & METH_STATIC:
                    w_func = PyCFunction_NewEx(space, method, None)
                    w_obj = space.w_Ellipsis # XXX
                    #w_obj = PyStaticMethod_New(space, w_func)
                else:
                    w_obj = PyDescr_NewMethod(space, pto, method)

            dict_w[methodname] = w_obj


@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyModule_Check(space, w_obj):
    w_type = space.gettypeobject(Module.typedef)
    w_obj_type = space.type(w_obj)
    return int(space.is_w(w_type, w_obj_type) or
               space.is_true(space.issubtype(w_obj_type, w_type)))

@cpython_api([PyObject], PyObject, borrowed=True)
def PyModule_GetDict(space, w_mod):
    if PyModule_Check(space, w_mod):
        assert isinstance(w_mod, Module)
        w_dict = w_mod.getdict()
        register_container(space, w_mod)
        return w_dict
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject], rffi.CCHARP, error=0)
def PyModule_GetName(space, module):
    """
    Return module's __name__ value.  If the module does not provide one,
    or if it is not a string, SystemError is raised and NULL is returned."""
    raise NotImplementedError


