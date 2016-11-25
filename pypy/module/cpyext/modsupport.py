from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, cpython_struct, \
        METH_STATIC, METH_CLASS, METH_COEXIST, CANNOT_FAIL, CONST_STRING
from pypy.module.cpyext.pyobject import PyObject, as_pyobj
from pypy.interpreter.module import Module
from pypy.module.cpyext.methodobject import (
    W_PyCFunctionObject, PyCFunction_NewEx, PyDescr_NewMethod,
    PyMethodDef, PyDescr_NewClassMethod, PyStaticMethod_New)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.module.cpyext.state import State
from pypy.interpreter.error import oefmt

PyModuleDef_BaseStruct = cpython_struct(
    'PyModuleDef_Base',
    [])

PyModuleDefStruct = cpython_struct(
    'PyModuleDef',
    [('m_base', PyModuleDef_BaseStruct),
     ('m_name', rffi.CCHARP),
     ('m_doc', rffi.CCHARP),
     ('m_methods', lltype.Ptr(PyMethodDef)),
     ], level=2)
PyModuleDef = lltype.Ptr(PyModuleDefStruct)

@cpython_api([PyModuleDef, rffi.INT_real], PyObject)
def PyModule_Create2(space, module, api_version):
    """Create a new module object, given the definition in module, assuming the
    API version module_api_version.  If that version does not match the version
    of the running interpreter, a RuntimeWarning is emitted.
    
    Most uses of this function should be using PyModule_Create()
    instead; only use this if you are sure you need it."""

    modname = rffi.charp2str(module.c_m_name)
    if module.c_m_doc:
        doc = rffi.charp2str(module.c_m_doc)
    else:
        doc = None
    methods = module.c_m_methods

    state = space.fromcache(State)
    f_name, f_path = state.package_context
    if f_name is not None:
        modname = f_name
    w_mod = space.wrap(Module(space, space.wrap(modname)))
    state.package_context = None, None

    if f_path is not None:
        dict_w = {'__file__': space.wrap_fsdecoded(f_path)}
    else:
        dict_w = {}
    convert_method_defs(space, dict_w, methods, None, w_mod, modname)
    for key, w_value in dict_w.items():
        space.setattr(w_mod, space.wrap(key), w_value)
    if doc:
        space.setattr(w_mod, space.wrap("__doc__"),
                      space.wrap(doc))
    return w_mod


def convert_method_defs(space, dict_w, methods, w_type, w_self=None, name=None):
    w_name = space.wrap(name)
    methods = rffi.cast(rffi.CArrayPtr(PyMethodDef), methods)
    if methods:
        i = -1
        while True:
            i = i + 1
            method = methods[i]
            if not method.c_ml_name: break

            methodname = rffi.charp2str(rffi.cast(rffi.CCHARP, method.c_ml_name))
            flags = rffi.cast(lltype.Signed, method.c_ml_flags)

            if w_type is None:
                if flags & METH_CLASS or flags & METH_STATIC:
                    raise oefmt(space.w_ValueError,
                            "module functions cannot set METH_CLASS or "
                            "METH_STATIC")
                w_obj = space.wrap(W_PyCFunctionObject(space, method, w_self, w_name))
            else:
                if methodname in dict_w and not (flags & METH_COEXIST):
                    continue
                if flags & METH_CLASS:
                    if flags & METH_STATIC:
                        raise oefmt(space.w_ValueError,
                                    "method cannot be both class and static")
                    w_obj = PyDescr_NewClassMethod(space, w_type, method)
                elif flags & METH_STATIC:
                    w_func = PyCFunction_NewEx(space, method, None, None)
                    w_obj = PyStaticMethod_New(space, w_func)
                else:
                    w_obj = PyDescr_NewMethod(space, w_type, method)

            dict_w[methodname] = w_obj


@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyModule_Check(space, w_obj):
    w_type = space.gettypeobject(Module.typedef)
    w_obj_type = space.type(w_obj)
    return int(space.is_w(w_type, w_obj_type) or
               space.issubtype_w(w_obj_type, w_type))

@cpython_api([PyObject], PyObject, result_borrowed=True)
def PyModule_GetDict(space, w_mod):
    if PyModule_Check(space, w_mod):
        assert isinstance(w_mod, Module)
        w_dict = w_mod.getdict(space)
        return w_dict    # borrowed reference, likely from w_mod.w_dict
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject], rffi.CCHARP)
def PyModule_GetName(space, w_mod):
    """
    Return module's __name__ value.  If the module does not provide one,
    or if it is not a string, SystemError is raised and NULL is returned.
    """
    # NOTE: this version of the code works only because w_mod.w_name is
    # a wrapped string object attached to w_mod; so it makes a
    # PyStringObject that will live as long as the module itself,
    # and returns a "char *" inside this PyStringObject.
    if not isinstance(w_mod, Module):
        raise oefmt(space.w_SystemError, "PyModule_GetName(): not a module")
    from pypy.module.cpyext.unicodeobject import _PyUnicode_AsString
    return _PyUnicode_AsString(space, as_pyobj(space, w_mod.w_name))
