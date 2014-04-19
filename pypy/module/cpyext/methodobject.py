from rpython.rtyper.lltypesystem import lltype, rffi

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.function import ClassMethod, Method, StaticMethod
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import (
    GetSetProperty, TypeDef, interp_attrproperty, interp_attrproperty_w)
from pypy.module.cpyext.api import (
    CONST_STRING, METH_CLASS, METH_COEXIST, METH_KEYWORDS, METH_NOARGS, METH_O,
    METH_STATIC, METH_VARARGS, PyObject, PyObjectFields, bootstrap_function,
    build_type_checkers, cpython_api, cpython_struct, generic_cpy_call)
from pypy.module.cpyext.pyobject import (
    Py_DecRef, from_ref, make_ref, make_typedescr)

PyCFunction_typedef = rffi.COpaquePtr(typedef='PyCFunction')
PyCFunction = lltype.Ptr(lltype.FuncType([PyObject, PyObject], PyObject))
PyCFunctionKwArgs = lltype.Ptr(lltype.FuncType([PyObject, PyObject, PyObject],
                                               PyObject))

PyMethodDef = cpython_struct(
    'PyMethodDef',
    [('ml_name', rffi.CCHARP),
     ('ml_meth', PyCFunction_typedef),
     ('ml_flags', rffi.INT_real),
     ('ml_doc', rffi.CCHARP),
     ])

PyCFunctionObjectStruct = cpython_struct(
    'PyCFunctionObject',
    PyObjectFields + (
     ('m_ml', lltype.Ptr(PyMethodDef)),
     ('m_self', PyObject),
     ('m_module', PyObject),
     ))
PyCFunctionObject = lltype.Ptr(PyCFunctionObjectStruct)

@bootstrap_function
def init_methodobject(space):
    make_typedescr(W_PyCFunctionObject.typedef,
                   basestruct=PyCFunctionObject.TO,
                   attach=cfunction_attach,
                   dealloc=cfunction_dealloc)

def cfunction_attach(space, py_obj, w_obj):
    py_func = rffi.cast(PyCFunctionObject, py_obj)
    assert isinstance(w_obj, W_PyCFunctionObject)
    py_func.c_m_ml = w_obj.ml
    py_func.c_m_self = make_ref(space, w_obj.w_self)
    py_func.c_m_module = make_ref(space, w_obj.w_module)

@cpython_api([PyObject], lltype.Void, external=False)
def cfunction_dealloc(space, py_obj):
    py_func = rffi.cast(PyCFunctionObject, py_obj)
    Py_DecRef(space, py_func.c_m_self)
    Py_DecRef(space, py_func.c_m_module)
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, py_obj)


class W_PyCFunctionObject(W_Root):
    def __init__(self, space, ml, w_self, w_module=None):
        self.ml = ml
        self.name = rffi.charp2str(self.ml.c_ml_name)
        self.w_self = w_self
        self.w_module = w_module

    def call(self, space, w_self, w_args, w_kw):
        # Call the C function
        if w_self is None:
            w_self = self.w_self
        flags = rffi.cast(lltype.Signed, self.ml.c_ml_flags)
        flags &= ~(METH_CLASS | METH_STATIC | METH_COEXIST)
        if space.is_true(w_kw) and not flags & METH_KEYWORDS:
            raise OperationError(space.w_TypeError, space.wrap(
                self.name + "() takes no keyword arguments"))

        func = rffi.cast(PyCFunction, self.ml.c_ml_meth)
        length = space.int_w(space.len(w_args))
        if flags & METH_KEYWORDS:
            func = rffi.cast(PyCFunctionKwArgs, self.ml.c_ml_meth)
            return generic_cpy_call(space, func, w_self, w_args, w_kw)
        elif flags & METH_NOARGS:
            if length == 0:
                return generic_cpy_call(space, func, w_self, None)
            raise OperationError(space.w_TypeError, space.wrap(
                self.name + "() takes no arguments"))
        elif flags & METH_O:
            if length != 1:
                raise oefmt(space.w_TypeError,
                            "%s() takes exactly one argument (%d given)",
                            self.name, length)
            w_arg = space.getitem(w_args, space.wrap(0))
            return generic_cpy_call(space, func, w_self, w_arg)
        elif flags & METH_VARARGS:
            return generic_cpy_call(space, func, w_self, w_args)
        else: # METH_OLDARGS, the really old style
            size = length
            if size == 1:
                w_arg = space.getitem(w_args, space.wrap(0))
            elif size == 0:
                w_arg = None
            else:
                w_arg = w_args
            return generic_cpy_call(space, func, w_self, w_arg)

    def get_doc(self, space):
        doc = self.ml.c_ml_doc
        if doc:
            return space.wrap(rffi.charp2str(doc))
        else:
            return space.w_None


class W_PyCMethodObject(W_PyCFunctionObject):
    w_self = None
    def __init__(self, space, ml, w_type):
        self.space = space
        self.ml = ml
        self.name = rffi.charp2str(ml.c_ml_name)
        self.w_objclass = w_type

    def __repr__(self):
        return self.space.unwrap(self.descr_method_repr())

    def descr_method_repr(self):
        return self.getrepr(self.space,
                            "built-in method '%s' of '%s' object" %
                            (self.name, self.w_objclass.getname(self.space)))

PyCFunction_Check, PyCFunction_CheckExact = build_type_checkers(
    "CFunction", W_PyCFunctionObject)

class W_PyCClassMethodObject(W_PyCFunctionObject):
    w_self = None
    def __init__(self, space, ml, w_type):
        self.space = space
        self.ml = ml
        self.name = rffi.charp2str(ml.c_ml_name)
        self.w_objclass = w_type

    def __repr__(self):
        return self.space.unwrap(self.descr_method_repr())

    def descr_method_repr(self):
        return self.getrepr(self.space,
                            "built-in method '%s' of '%s' object" %
                            (self.name, self.w_objclass.getname(self.space)))


class W_PyCWrapperObject(W_Root):
    def __init__(self, space, pto, method_name, wrapper_func,
                 wrapper_func_kwds, doc, func):
        self.space = space
        self.method_name = method_name
        self.wrapper_func = wrapper_func
        self.wrapper_func_kwds = wrapper_func_kwds
        self.doc = doc
        self.func = func
        pyo = rffi.cast(PyObject, pto)
        self.w_objclass = from_ref(space, pyo)

    def call(self, space, w_self, w_args, w_kw):
        if self.wrapper_func is None:
            assert self.wrapper_func_kwds is not None
            return self.wrapper_func_kwds(space, w_self, w_args, self.func,
                                          w_kw)
        if space.is_true(w_kw):
            raise oefmt(space.w_TypeError,
                        "wrapper %s doesn't take any keyword arguments",
                        self.method_name)
        return self.wrapper_func(space, w_self, w_args, self.func)

    def descr_method_repr(self):
        return self.space.wrap("<slot wrapper '%s' of '%s' objects>" %
                               (self.method_name,
                                self.w_objclass.getname(self.space)))

def cwrapper_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCWrapperObject, w_self)
    args_w, kw_w = __args__.unpack()
    w_args = space.newtuple(args_w[1:])
    w_self = args_w[0]
    w_kw = space.newdict()
    for key, w_obj in kw_w.items():
        space.setitem(w_kw, space.wrap(key), w_obj)
    return self.call(space, w_self, w_args, w_kw)


def cfunction_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCFunctionObject, w_self)
    args_w, kw_w = __args__.unpack()
    w_args = space.newtuple(args_w)
    w_kw = space.newdict()
    for key, w_obj in kw_w.items():
        space.setitem(w_kw, space.wrap(key), w_obj)
    ret = self.call(space, None, w_args, w_kw)
    return ret

def cmethod_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCFunctionObject, w_self)
    args_w, kw_w = __args__.unpack()
    w_instance = args_w[0] # XXX typecheck missing
    w_args = space.newtuple(args_w[1:])
    w_kw = space.newdict()
    for key, w_obj in kw_w.items():
        space.setitem(w_kw, space.wrap(key), w_obj)
    ret = self.call(space, w_instance, w_args, w_kw)
    return ret

def cmethod_descr_get(space, w_function, w_obj, w_cls=None):
    asking_for_bound = (space.is_none(w_cls) or
                        not space.is_w(w_obj, space.w_None) or
                        space.is_w(w_cls, space.type(space.w_None)))
    if asking_for_bound:
        return space.wrap(Method(space, w_function, w_obj, w_cls))
    else:
        return w_function

def cclassmethod_descr_get(space, w_function, w_obj, w_cls=None):
    if not w_cls:
        w_cls = space.type(w_obj)
    return space.wrap(Method(space, w_function, w_cls, space.w_None))


W_PyCFunctionObject.typedef = TypeDef(
    'builtin_function_or_method',
    __call__ = interp2app(cfunction_descr_call),
    __doc__ = GetSetProperty(W_PyCFunctionObject.get_doc),
    __module__ = interp_attrproperty_w('w_module', cls=W_PyCFunctionObject),
    __name__ = interp_attrproperty('name', cls=W_PyCFunctionObject),
    )
W_PyCFunctionObject.typedef.acceptable_as_base_class = False

W_PyCMethodObject.typedef = TypeDef(
    'method',
    __get__ = interp2app(cmethod_descr_get),
    __call__ = interp2app(cmethod_descr_call),
    __name__ = interp_attrproperty('name', cls=W_PyCMethodObject),
    __objclass__ = interp_attrproperty_w('w_objclass', cls=W_PyCMethodObject),
    __repr__ = interp2app(W_PyCMethodObject.descr_method_repr),
    )
W_PyCMethodObject.typedef.acceptable_as_base_class = False

W_PyCClassMethodObject.typedef = TypeDef(
    'classmethod',
    __get__ = interp2app(cclassmethod_descr_get),
    __call__ = interp2app(cmethod_descr_call),
    __name__ = interp_attrproperty('name', cls=W_PyCClassMethodObject),
    __objclass__ = interp_attrproperty_w('w_objclass',
                                         cls=W_PyCClassMethodObject),
    __repr__ = interp2app(W_PyCClassMethodObject.descr_method_repr),
    )
W_PyCClassMethodObject.typedef.acceptable_as_base_class = False


W_PyCWrapperObject.typedef = TypeDef(
    'wrapper_descriptor',
    __call__ = interp2app(cwrapper_descr_call),
    __get__ = interp2app(cmethod_descr_get),
    __name__ = interp_attrproperty('method_name', cls=W_PyCWrapperObject),
    __doc__ = interp_attrproperty('doc', cls=W_PyCWrapperObject),
    __objclass__ = interp_attrproperty_w('w_objclass', cls=W_PyCWrapperObject),
    __repr__ = interp2app(W_PyCWrapperObject.descr_method_repr),
    # XXX missing: __getattribute__
    )
W_PyCWrapperObject.typedef.acceptable_as_base_class = False


@cpython_api([lltype.Ptr(PyMethodDef), PyObject, PyObject], PyObject)
def PyCFunction_NewEx(space, ml, w_self, w_name):
    return space.wrap(W_PyCFunctionObject(space, ml, w_self, w_name))

@cpython_api([PyObject], PyCFunction_typedef)
def PyCFunction_GetFunction(space, w_obj):
    cfunction = space.interp_w(W_PyCFunctionObject, w_obj)
    return cfunction.ml.c_ml_meth

@cpython_api([PyObject], PyObject)
def PyStaticMethod_New(space, w_func):
    return space.wrap(StaticMethod(w_func))

@cpython_api([PyObject], PyObject)
def PyClassMethod_New(space, w_func):
    return space.wrap(ClassMethod(w_func))

@cpython_api([PyObject, lltype.Ptr(PyMethodDef)], PyObject)
def PyDescr_NewMethod(space, w_type, method):
    return space.wrap(W_PyCMethodObject(space, method, w_type))

@cpython_api([PyObject, lltype.Ptr(PyMethodDef)], PyObject)
def PyDescr_NewClassMethod(space, w_type, method):
    return space.wrap(W_PyCClassMethodObject(space, method, w_type))

def PyDescr_NewWrapper(space, pto, method_name, wrapper_func,
                       wrapper_func_kwds, doc, func):
    # not exactly the API sig
    return space.wrap(W_PyCWrapperObject(space, pto, method_name,
        wrapper_func, wrapper_func_kwds, doc, func))

@cpython_api([lltype.Ptr(PyMethodDef), PyObject, CONST_STRING], PyObject)
def Py_FindMethod(space, table, w_obj, name_ptr):
    """Return a bound method object for an extension type implemented in
    C.  This can be useful in the implementation of a tp_getattro or
    tp_getattr handler that does not use the PyObject_GenericGetAttr()
    function.
    """
    # XXX handle __doc__

    name = rffi.charp2str(name_ptr)
    methods = rffi.cast(rffi.CArrayPtr(PyMethodDef), table)
    method_list_w = []

    if methods:
        i = -1
        while True:
            i = i + 1
            method = methods[i]
            if not method.c_ml_name:
                break
            if name == "__methods__":
                method_list_w.append(
                    space.wrap(rffi.charp2str(method.c_ml_name)))
            elif rffi.charp2str(method.c_ml_name) == name: # XXX expensive copy
                return space.wrap(W_PyCFunctionObject(space, method, w_obj))
    if name == "__methods__":
        return space.newlist(method_list_w)
    raise OperationError(space.w_AttributeError, space.wrap(name))

