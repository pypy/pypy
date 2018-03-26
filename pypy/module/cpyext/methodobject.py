from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib import jit

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.function import ClassMethod, Method, StaticMethod
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import (
    GetSetProperty, TypeDef, interp_attrproperty, interp_attrproperty_w)
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.module.cpyext.api import (
    CONST_STRING, METH_CLASS, METH_COEXIST, METH_KEYWORDS, METH_NOARGS, METH_O,
    METH_STATIC, METH_VARARGS, PyObject, bootstrap_function,
    cpython_api, generic_cpy_call, CANNOT_FAIL, slot_function, cts,
    build_type_checkers)
from pypy.module.cpyext.pyobject import (
    decref, from_ref, make_ref, as_pyobj, make_typedescr)
from pypy.module.cpyext.state import State
from pypy.module.cpyext.tupleobject import tuple_from_args_w

PyMethodDef = cts.gettype('PyMethodDef')
PyCFunction = cts.gettype('PyCFunction')
PyCFunctionKwArgs = cts.gettype('PyCFunctionWithKeywords')
PyCFunctionObject = cts.gettype('PyCFunctionObject*')

@bootstrap_function
def init_methodobject(space):
    make_typedescr(W_PyCFunctionObject.typedef,
                   basestruct=PyCFunctionObject.TO,
                   attach=cfunction_attach,
                   dealloc=cfunction_dealloc)

def cfunction_attach(space, py_obj, w_obj, w_userdata=None):
    assert isinstance(w_obj, W_PyCFunctionObject)
    py_func = rffi.cast(PyCFunctionObject, py_obj)
    py_func.c_m_ml = w_obj.ml
    py_func.c_m_self = make_ref(space, w_obj.w_self)
    py_func.c_m_module = make_ref(space, w_obj.w_module)

@slot_function([PyObject], lltype.Void)
def cfunction_dealloc(space, py_obj):
    py_func = rffi.cast(PyCFunctionObject, py_obj)
    decref(space, py_func.c_m_self)
    decref(space, py_func.c_m_module)
    from pypy.module.cpyext.object import _dealloc
    _dealloc(space, py_obj)

def w_kwargs_from_args(space, __args__):
    w_kwargs = None
    if __args__.keywords:
        # CCC: we should probably have a @jit.look_inside_iff if the
        # keyword count is constant, as we do in Arguments.unpack
        w_kwargs = space.newdict()
        for i in range(len(__args__.keywords)):
            key = __args__.keywords[i]
            w_obj = __args__.keywords_w[i]
            space.setitem(w_kwargs, space.newtext(key), w_obj)
    return w_kwargs

def undotted_name(name):
    """Return the last component of a dotted name"""
    dotpos = name.rfind('.')
    if dotpos < 0:
        return name
    else:
        return name[dotpos + 1:]

SIGNATURE_MARKER = ')\n--\n\n'

def extract_doc(raw_doc, name):
    doc = raw_doc
    name = undotted_name(name)
    if raw_doc.startswith(name + '('):
        end_sig = raw_doc.find(SIGNATURE_MARKER)
        if end_sig > 0:
            doc = raw_doc[end_sig + len(SIGNATURE_MARKER):]
    if not doc:
        return None
    return doc

def extract_txtsig(raw_doc, name):
    name = undotted_name(name)
    if raw_doc.startswith(name + '('):
        end_sig = raw_doc.find(SIGNATURE_MARKER)
        if end_sig > 0:
            # Notes:
            # * Parentheses are included
            # * SIGNATURE_MARKER cannot appear inside name,
            #   so end_sig > len(name)
            return raw_doc[len(name): end_sig + 1]
    return None

class W_PyCFunctionObject(W_Root):
    _immutable_fields_ = ["flags"]

    def __init__(self, space, ml, w_self, w_module=None):
        self.ml = ml
        self.name = rffi.charp2str(rffi.cast(rffi.CCHARP, self.ml.c_ml_name))
        self.flags = rffi.cast(lltype.Signed, self.ml.c_ml_flags)
        self.w_self = w_self
        self.w_module = w_module

    def descr_call(self, space, __args__):
        return self.call(space, self.w_self, __args__)

    def call(self, space, w_self, __args__):
        flags = self.flags & ~(METH_CLASS | METH_STATIC | METH_COEXIST)
        length = len(__args__.arguments_w)
        if not flags & METH_KEYWORDS and __args__.keywords:
            raise oefmt(space.w_TypeError,
                        "%s() takes no keyword arguments", self.name)
        if flags & METH_KEYWORDS:
            return self.call_keywords(space, w_self, __args__)
        elif flags & METH_NOARGS:
            if length == 0:
                return self.call_noargs(space, w_self, __args__)
            raise oefmt(space.w_TypeError,
                        "%s() takes no arguments", self.name)
        elif flags & METH_O:
            if length != 1:
                raise oefmt(space.w_TypeError,
                            "%s() takes exactly one argument (%d given)",
                            self.name, length)
            return self.call_o(space, w_self, __args__)
        elif flags & METH_VARARGS:
            return self.call_varargs(space, w_self, __args__)
        else:  # shouldn't happen!
            raise oefmt(space.w_RuntimeError, "unknown calling convention")

    def call_noargs(self, space, w_self, __args__):
        func = self.ml.c_ml_meth
        return generic_cpy_call(space, func, w_self, None)

    def call_o(self, space, w_self, __args__):
        func = self.ml.c_ml_meth
        w_o = __args__.arguments_w[0]        
        return generic_cpy_call(space, func, w_self, w_o)

    def call_varargs(self, space, w_self, __args__):
        state = space.fromcache(State)
        func = self.ml.c_ml_meth
        py_args = tuple_from_args_w(space, __args__.arguments_w)
        try:
            return generic_cpy_call(space, func, w_self, py_args)
        finally:
            decref(space, py_args)

    def call_keywords(self, space, w_self, __args__):
        func = rffi.cast(PyCFunctionKwArgs, self.ml.c_ml_meth)
        py_args = tuple_from_args_w(space, __args__.arguments_w)
        w_kwargs = w_kwargs_from_args(space, __args__)
        try:
            return generic_cpy_call(space, func, w_self, py_args, w_kwargs)
        finally:
            decref(space, py_args)

    def get_doc(self, space):
        c_doc = self.ml.c_ml_doc
        if c_doc:
            rawdoc = rffi.charp2str(rffi.cast(rffi.CCHARP, c_doc))
            doc = extract_doc(rawdoc, self.name)
            if doc is not None:
                return space.newtext(doc)
        return space.w_None

    def get_txtsig(self, space):
        c_doc = self.ml.c_ml_doc
        if c_doc:
            rawdoc = rffi.charp2str(rffi.cast(rffi.CCHARP, c_doc))
            txtsig = extract_txtsig(rawdoc, self.name)
            if txtsig is not None:
                return space.newtext(txtsig)
        return space.w_None

class W_PyCMethodObject(W_PyCFunctionObject):

    def __init__(self, space, ml, w_type):
        W_PyCFunctionObject.__init__(self, space, ml, w_self=None)
        self.space = space
        self.w_objclass = w_type

    def __repr__(self):
        return self.space.unwrap(self.descr_method_repr())

    def descr_method_repr(self):
        w_objclass = self.w_objclass
        assert isinstance(w_objclass, W_TypeObject)
        return self.space.newtext("<method '%s' of '%s' objects>" % (
            self.name, w_objclass.name))

    def descr_call(self, space, __args__):
        if len(__args__.arguments_w) == 0:
            w_objclass = self.w_objclass
            assert isinstance(w_objclass, W_TypeObject)
            raise oefmt(space.w_TypeError,
                "descriptor '%8' of '%s' object needs an argument",
                self.name, self.w_objclass.getname(space))
        w_instance = __args__.arguments_w[0]
        # XXX: needs a stricter test
        if not space.isinstance_w(w_instance, self.w_objclass):
            w_objclass = self.w_objclass
            assert isinstance(w_objclass, W_TypeObject)
            raise oefmt(space.w_TypeError,
                "descriptor '%8' requires a '%s' object but received a '%T'",
                self.name, w_objclass.name, w_instance)
        #
        # CCC: we can surely do better than this
        __args__ = __args__.replace_arguments(__args__.arguments_w[1:])
        return self.call(space, w_instance, __args__)

# PyPy addition, for Cython
_, _ = build_type_checkers("MethodDescr", W_PyCMethodObject)


@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyCFunction_Check(space, w_obj):
    from pypy.interpreter.function import BuiltinFunction
    if w_obj is None:
        return False
    if isinstance(w_obj, W_PyCFunctionObject):
        return True
    return isinstance(w_obj, BuiltinFunction)

class W_PyCClassMethodObject(W_PyCFunctionObject):

    def __init__(self, space, ml, w_type):
        W_PyCFunctionObject.__init__(self, space, ml, w_self=None)
        self.space = space
        self.w_objclass = w_type

    def __repr__(self):
        return self.space.unwrap(self.descr_method_repr())

    def descr_call(self, space, __args__):
        if len(__args__.arguments_w) == 0:
            raise oefmt(space.w_TypeError,
                "descriptor '%8' of '%s' object needs an argument",
                self.name, self.w_objclass.getname(space))
        w_instance = __args__.arguments_w[0] # XXX typecheck missing
        # CCC: we can surely do better than this
        __args__ = __args__.replace_arguments(__args__.arguments_w[1:])
        return self.call(space, w_instance, __args__)

    def descr_method_repr(self):
        return self.getrepr(
            self.space, u"built-in method '%s' of '%s' object" %
            (self.name.decode('utf-8'), self.w_objclass.getname(self.space)))


class W_PyCWrapperObject(W_Root):
    """
    Abstract class; for concrete subclasses, see slotdefs.py
    """
    _immutable_fields_ = ['offset[*]']

    def __init__(self, space, pto, method_name, doc, func, offset):
        self.space = space
        self.method_name = method_name
        self.doc = doc
        self.func = func
        self.offset = offset
        pyo = rffi.cast(PyObject, pto)
        w_type = from_ref(space, pyo)
        assert isinstance(w_type, W_TypeObject)
        self.w_objclass = w_type

    def descr_call(self, space, w_self, __args__):
        return self.call(space, w_self, __args__)

    def call(self, space, w_self, __args__):
        raise NotImplementedError

    @jit.unroll_safe
    def get_func_to_call(self):
        func_to_call = self.func
        if self.offset:
            pto = as_pyobj(self.space, self.w_objclass)
            # make ptr the equivalent of this, using the offsets
            #func_to_call = rffi.cast(rffi.VOIDP, ptr.c_tp_as_number.c_nb_multiply)
            if pto:
                cptr = rffi.cast(rffi.CCHARP, pto)
                for o in self.offset:
                    ptr = rffi.cast(rffi.VOIDPP, rffi.ptradd(cptr, o))[0]
                    cptr = rffi.cast(rffi.CCHARP, ptr)
                func_to_call = rffi.cast(rffi.VOIDP, cptr)
            else:
                # Should never happen, assert to get a traceback
                assert False, "failed to convert w_type %s to PyObject" % str(
                                                              self.w_objclass)
        assert func_to_call
        return func_to_call

    def check_args(self, __args__, arity):
        length = len(__args__.arguments_w)
        if length != arity:
            raise oefmt(self.space.w_TypeError, "expected %d arguments, got %d",
                        arity, length)
        if __args__.keywords:
            raise oefmt(self.space.w_TypeError,
                        "wrapper %s doesn't take any keyword arguments",
                        self.method_name)

    def check_argsv(self, __args__, min, max):
        length = len(__args__.arguments_w)
        if not min <= length <= max:
            raise oefmt(self.space.w_TypeError, "expected %d-%d arguments, got %d",
                        min, max, length)
        if __args__.keywords:
            raise oefmt(self.space.w_TypeError,
                        "wrapper %s doesn't take any keyword arguments",
                        self.method_name)

    def descr_method_repr(self):
        return self.space.newtext("<slot wrapper '%s' of '%s' objects>" %
                                  (self.method_name,
                                   self.w_objclass.name))


def cmethod_descr_get(space, w_function, w_obj, w_cls=None):
    if w_obj is None or space.is_w(w_obj, space.w_None):
        return w_function
    else:
        return Method(space, w_function, w_obj)

def cclassmethod_descr_get(space, w_function, w_obj, w_cls=None):
    if not w_cls:
        w_cls = space.type(w_obj)
    return Method(space, w_function, w_cls)


W_PyCFunctionObject.typedef = TypeDef(
    'builtin_function_or_method',
    __call__ = interp2app(W_PyCFunctionObject.descr_call),
    __doc__ = GetSetProperty(W_PyCFunctionObject.get_doc),
    __text_signature__ = GetSetProperty(W_PyCFunctionObject.get_txtsig),
    __module__ = interp_attrproperty_w('w_module', cls=W_PyCFunctionObject),
    __name__ = interp_attrproperty('name', cls=W_PyCFunctionObject,
        wrapfn="newtext_or_none"),
    )
W_PyCFunctionObject.typedef.acceptable_as_base_class = False

W_PyCMethodObject.typedef = TypeDef(
    'method_descriptor',
    __get__ = interp2app(cmethod_descr_get),
    __call__ = interp2app(W_PyCMethodObject.descr_call),
    __name__ = interp_attrproperty('name', cls=W_PyCMethodObject,
        wrapfn="newtext_or_none"),
    __objclass__ = interp_attrproperty_w('w_objclass', cls=W_PyCMethodObject),
    __repr__ = interp2app(W_PyCMethodObject.descr_method_repr),
    )
W_PyCMethodObject.typedef.acceptable_as_base_class = False

W_PyCClassMethodObject.typedef = TypeDef(
    'classmethod',
    __get__ = interp2app(cclassmethod_descr_get),
    __call__ = interp2app(W_PyCClassMethodObject.descr_call),
    __name__ = interp_attrproperty('name', cls=W_PyCClassMethodObject,
        wrapfn="newtext_or_none"),
    __objclass__ = interp_attrproperty_w('w_objclass',
                                         cls=W_PyCClassMethodObject),
    __repr__ = interp2app(W_PyCClassMethodObject.descr_method_repr),
    )
W_PyCClassMethodObject.typedef.acceptable_as_base_class = False


W_PyCWrapperObject.typedef = TypeDef(
    'wrapper_descriptor',
    __call__ = interp2app(W_PyCWrapperObject.descr_call),
    __get__ = interp2app(cmethod_descr_get),
    __name__ = interp_attrproperty('method_name', cls=W_PyCWrapperObject,
        wrapfn="newtext_or_none"),
    __doc__ = interp_attrproperty('doc', cls=W_PyCWrapperObject,
        wrapfn="newtext_or_none"),
    __objclass__ = interp_attrproperty_w('w_objclass', cls=W_PyCWrapperObject),
    __repr__ = interp2app(W_PyCWrapperObject.descr_method_repr),
    # XXX missing: __getattribute__
    )
W_PyCWrapperObject.typedef.acceptable_as_base_class = False


@cpython_api([lltype.Ptr(PyMethodDef), PyObject, PyObject], PyObject)
def PyCFunction_NewEx(space, ml, w_self, w_name):
    return W_PyCFunctionObject(space, ml, w_self, w_name)

@cts.decl("PyCFunction PyCFunction_GetFunction(PyObject *)")
def PyCFunction_GetFunction(space, w_obj):
    try:
        cfunction = space.interp_w(W_PyCFunctionObject, w_obj)
    except OperationError as e:
        if e.match(space, space.w_TypeError):
            raise oefmt(space.w_SystemError,
                        "bad argument to internal function")
        raise
    return cfunction.ml.c_ml_meth

@cpython_api([PyObject], PyObject)
def PyStaticMethod_New(space, w_func):
    return StaticMethod(w_func)

@cpython_api([PyObject], PyObject)
def PyClassMethod_New(space, w_func):
    return ClassMethod(w_func)

@cts.decl("""
    PyObject *
    PyDescr_NewClassMethod(PyTypeObject *type, PyMethodDef *method)""")
def PyDescr_NewMethod(space, w_type, method):
    return W_PyCMethodObject(space, method, w_type)

@cts.decl("""
    PyObject *
    PyDescr_NewClassMethod(PyTypeObject *type, PyMethodDef *method)""")
def PyDescr_NewClassMethod(space, w_type, method):
    return W_PyCClassMethodObject(space, method, w_type)

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
                method_list_w.append(space.newtext(rffi.charp2str(
                    rffi.cast(rffi.CCHARP, method.c_ml_name))))
            elif rffi.charp2str(rffi.cast(rffi.CCHARP, method.c_ml_name)) == name: # XXX expensive copy
                return W_PyCFunctionObject(space, method, w_obj)
    if name == "__methods__":
        return space.newlist(method_list_w)
    raise OperationError(space.w_AttributeError, space.newtext(name))
