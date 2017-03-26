from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, METH_STATIC, METH_CLASS, METH_COEXIST, CANNOT_FAIL, cts,
    parse_dir, bootstrap_function, generic_cpy_call)
from pypy.module.cpyext.pyobject import PyObject, as_pyobj, make_typedescr
from pypy.interpreter.module import Module
from pypy.module.cpyext.methodobject import (
    W_PyCFunctionObject, PyCFunction_NewEx, PyDescr_NewMethod,
    PyMethodDef, PyDescr_NewClassMethod, PyStaticMethod_New)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.module.cpyext.state import State
from pypy.interpreter.error import oefmt

cts.parse_header(parse_dir / 'cpyext_moduleobject.h')
PyModuleDef = cts.gettype('PyModuleDef *')
PyModuleObject = cts.gettype('PyModuleObject *')
PyModuleDef_Slot = cts.gettype('PyModuleDef_Slot')

@bootstrap_function
def init_moduleobject(space):
    make_typedescr(Module.typedef, basestruct=PyModuleObject.TO)

@cpython_api([rffi.CCHARP], PyObject)
def PyModule_New(space, name):
    """
    Return a new module object with the __name__ attribute set to name.
    Only the module's __doc__ and __name__ attributes are filled in;
    the caller is responsible for providing a __file__ attribute."""
    return Module(space, space.newtext(rffi.charp2str(name)))

@cpython_api([PyModuleDef, rffi.INT_real], PyObject)
def PyModule_Create2(space, module, api_version):
    """Create a new module object, given the definition in module, assuming the
    API version module_api_version.  If that version does not match the version
    of the running interpreter, a RuntimeWarning is emitted.

    Most uses of this function should be using PyModule_Create()
    instead; only use this if you are sure you need it."""

    modname = rffi.charp2str(rffi.cast(rffi.CCHARP, module.c_m_name))
    if module.c_m_doc:
        doc = rffi.charp2str(rffi.cast(rffi.CCHARP, module.c_m_doc))
    else:
        doc = None
    methods = module.c_m_methods

    state = space.fromcache(State)
    f_name, f_path = state.package_context
    if f_name is not None:
        modname = f_name
    w_mod = Module(space, space.newtext(modname))
    rffi.cast(PyModuleObject, as_pyobj(space, w_mod)).c_md_def = module
    state.package_context = None, None

    if f_path is not None:
        dict_w = {'__file__': space.newfilename(f_path)}
    else:
        dict_w = {}
    convert_method_defs(space, dict_w, methods, None, w_mod, modname)
    for key, w_value in dict_w.items():
        space.setattr(w_mod, space.newtext(key), w_value)
    if doc:
        space.setattr(w_mod, space.newtext("__doc__"),
                      space.newtext(doc))
    return w_mod


createfunctype = lltype.Ptr(lltype.FuncType([PyObject, PyModuleDef], PyObject))
execfunctype = lltype.Ptr(lltype.FuncType([PyObject], rffi.INT_real))


def create_module_from_def_and_spec(space, moddef, w_spec, name):
    moddef = rffi.cast(PyModuleDef, moddef)
    if moddef.c_m_size < 0:
        raise oefmt(space.w_SystemError,
                    "module %s: m_size may not be negative for multi-phase "
                    "initialization", name)
    createf = lltype.nullptr(rffi.VOIDP.TO)
    has_execution_slots = False
    cur_slot = rffi.cast(rffi.CArrayPtr(PyModuleDef_Slot), moddef.c_m_slots)
    if cur_slot:
        while True:
            slot = rffi.cast(lltype.Signed, cur_slot[0].c_slot)
            if slot == 0:
                break
            elif slot == 1:
                if createf:
                    raise oefmt(space.w_SystemError,
                                "module %s has multiple create slots", name)
                createf = cur_slot[0].c_value
            elif slot < 0 or slot > 2:
                raise oefmt(space.w_SystemError,
                            "module %s uses unknown slot ID %d", name, slot)
            else:
                has_execution_slots = True
            cur_slot = rffi.ptradd(cur_slot, 1)
    if createf:
        createf = rffi.cast(createfunctype, createf)
        w_mod = generic_cpy_call(space, createf, w_spec, moddef)
    else:
        w_mod = Module(space, space.newtext(name))
    if isinstance(w_mod, Module):
        mod = rffi.cast(PyModuleObject, as_pyobj(space, w_mod))
        #mod.c_md_state = None
        mod.c_md_def = moddef
    else:
        if moddef.c_m_size > 0 or moddef.c_m_traverse or moddef.c_m_clear or \
           moddef.c_m_free:
            raise oefmt(space.w_SystemError,
                        "module %s is not a module object, but requests "
                        "module state", name)
        if has_execution_slots:
            raise oefmt(space.w_SystemError,
                        "module %s specifies execution slots, but did not "
                        "create a ModuleType instance", name)
    dict_w = {}
    convert_method_defs(space, dict_w, moddef.c_m_methods, None, w_mod, name)
    for key, w_value in dict_w.items():
        space.setattr(w_mod, space.newtext(key), w_value)
    if moddef.c_m_doc:
        doc = rffi.charp2str(rffi.cast(rffi.CCHARP, moddef.c_m_doc))
        space.setattr(w_mod, space.newtext('__doc__'), space.newtext(doc))
    return w_mod


def exec_def(space, w_mod, mod_as_pyobj):
    from pypy.module.cpyext.pyerrors import PyErr_Occurred
    mod = rffi.cast(PyModuleObject, mod_as_pyobj)
    moddef = mod.c_md_def
    cur_slot = rffi.cast(rffi.CArrayPtr(PyModuleDef_Slot), moddef.c_m_slots)
    while cur_slot and rffi.cast(lltype.Signed, cur_slot[0].c_slot):
        if rffi.cast(lltype.Signed, cur_slot[0].c_slot) == 2:
            execf = rffi.cast(execfunctype, cur_slot[0].c_value)
            res = generic_cpy_call(space, execf, w_mod)
            has_error = PyErr_Occurred(space) is not None
            if rffi.cast(lltype.Signed, res):
                if has_error:
                    state = space.fromcache(State)
                    state.check_and_raise_exception()
                else:
                    raise oefmt(space.w_SystemError,
                                "execution of module %S failed without "
                                "setting an exception", w_mod.w_name)
            if has_error:
                raise oefmt(space.w_SystemError,
                            "execution of module %S raised unreported "
                            "exception", w_mod.w_name)
        cur_slot = rffi.ptradd(cur_slot, 1)


def convert_method_defs(space, dict_w, methods, w_type, w_self=None, name=None):
    w_name = space.newtext_or_none(name)
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
                w_obj = W_PyCFunctionObject(space, method, w_self, w_name)
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
    from pypy.module.cpyext.unicodeobject import PyUnicode_AsUTF8
    return PyUnicode_AsUTF8(space, as_pyobj(space, w_mod.w_name))
