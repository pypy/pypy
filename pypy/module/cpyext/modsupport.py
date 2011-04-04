from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, cpython_struct, \
        METH_STATIC, METH_CLASS, METH_COEXIST, CANNOT_FAIL, CONST_STRING
from pypy.module.cpyext.pyobject import PyObject, borrow_from
from pypy.interpreter.module import Module
from pypy.module.cpyext.methodobject import (
    W_PyCFunctionObject, PyCFunction_NewEx, PyDescr_NewMethod,
    PyMethodDef, PyStaticMethod_New)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.module.cpyext.state import State
from pypy.interpreter.error import OperationError

#@cpython_api([rffi.CCHARP], PyObject)
def PyImport_AddModule(space, name):
    """Return the module object corresponding to a module name.  The name argument
    may be of the form package.module. First check the modules dictionary if
    there's one there, and if not, create a new one and insert it in the modules
    dictionary.

    This function does not load or import the module; if the module wasn't already
    loaded, you will get an empty module object. Use PyImport_ImportModule()
    or one of its variants to import a module.  Package structures implied by a
    dotted name for name are not created if not already present."""
    w_name = space.wrap(name)
    w_modules = space.sys.get('modules')

    w_mod = space.finditem_str(w_modules, name)
    if w_mod is None:
        w_mod = space.wrap(Module(space, w_name))
        space.setitem(w_modules, w_name, w_mod)

    return w_mod

# This is actually the Py_InitModule4 function,
# renamed to refuse modules built against CPython headers.
@cpython_api([CONST_STRING, lltype.Ptr(PyMethodDef), CONST_STRING,
              PyObject, rffi.INT_real], PyObject)
def _Py_InitPyPyModule(space, name, methods, doc, w_self, apiver):
    """
    Create a new module object based on a name and table of functions, returning
    the new module object. If doc is non-NULL, it will be used to define the
    docstring for the module. If self is non-NULL, it will passed to the
    functions of the module as their (otherwise NULL) first parameter. (This was
    added as an experimental feature, and there are no known uses in the current
    version of Python.) For apiver, the only value which should be passed is
    defined by the constant PYTHON_API_VERSION.

    Note that the name parameter is actually ignored, and the module name is
    taken from the package_context attribute of the cpyext.State in the space
    cache.  CPython includes some extra checking here to make sure the module
    being initialized lines up with what's expected, but we don't.
    """
    from pypy.module.cpyext.typeobjectdefs import PyTypeObjectPtr
    modname = rffi.charp2str(name)
    state = space.fromcache(State)
    f_name, f_path = state.package_context
    w_mod = PyImport_AddModule(space, f_name)

    dict_w = {'__file__': space.wrap(f_path)}
    convert_method_defs(space, dict_w, methods, None, w_self, modname)
    for key, w_value in dict_w.items():
        space.setattr(w_mod, space.wrap(key), w_value)
    if doc:
        space.setattr(w_mod, space.wrap("__doc__"),
                      space.wrap(rffi.charp2str(doc)))
    return borrow_from(None, w_mod)


def convert_method_defs(space, dict_w, methods, w_type, w_self=None, name=None):
    w_name = space.wrap(name)
    methods = rffi.cast(rffi.CArrayPtr(PyMethodDef), methods)
    if methods:
        i = -1
        while True:
            i = i + 1
            method = methods[i]
            if not method.c_ml_name: break

            methodname = rffi.charp2str(method.c_ml_name)
            flags = rffi.cast(lltype.Signed, method.c_ml_flags)

            if w_type is None:
                if flags & METH_CLASS or flags & METH_STATIC:
                    raise OperationError(space.w_ValueError,
                            space.wrap("module functions cannot set METH_CLASS or METH_STATIC"))
                w_obj = space.wrap(W_PyCFunctionObject(space, method, w_self, w_name))
            else:
                if methodname in dict_w and not (flags & METH_COEXIST):
                    continue
                if flags & METH_CLASS:
                    if flags & METH_STATIC:
                        raise OperationError(space.w_ValueError,
                                space.wrap("method cannot be both class and static"))
                    #w_obj = PyDescr_NewClassMethod(space, w_type, method)
                    w_obj = space.w_Ellipsis # XXX
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
               space.is_true(space.issubtype(w_obj_type, w_type)))

@cpython_api([PyObject], PyObject)
def PyModule_GetDict(space, w_mod):
    if PyModule_Check(space, w_mod):
        assert isinstance(w_mod, Module)
        w_dict = w_mod.getdict(space)
        return borrow_from(w_mod, w_dict)
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject], rffi.CCHARP, error=0)
def PyModule_GetName(space, module):
    """
    Return module's __name__ value.  If the module does not provide one,
    or if it is not a string, SystemError is raised and NULL is returned."""
    raise NotImplementedError


