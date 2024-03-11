import sys
from rpython.rtyper.lltypesystem import llmemory, lltype, rffi
from rpython.rlib import jit, clibffi, rgc
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.jit_libffi import CIF_DESCRIPTION, jit_ffi_call
from rpython.rlib.objectmodel import keepalive_until_here

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.function import ClassMethod, _Method, StaticMethod
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import (
    GetSetProperty, TypeDef, interp_attrproperty, interp_attrproperty_w,
    descr_generic_ne, make_weakref_descr)
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.module.cpyext.api import (
    CONST_STRING, METH_CLASS, METH_COEXIST, METH_KEYWORDS, METH_FASTCALL,
    METH_NOARGS, METH_O, METH_STATIC, METH_TYPED, METH_VARARGS, METH_METHOD,
    PyObject, bootstrap_function, cpython_api, generic_cpy_call,
    CANNOT_FAIL, slot_function, cts, build_type_checkers,
    PyObjectP, Py_ssize_t, include_dirs)
from pypy.module.cpyext.pyobject import (
    decref, from_ref, make_ref, make_typedescr, get_w_obj_and_decref)
from pypy.module.cpyext.state import State
from pypy.module.cpyext.tupleobject import tuple_from_args_w, PyTupleObject
from rpython.translator.tool.cbuild import ExternalCompilationInfo

PyMethodDef = cts.gettype('PyMethodDef')
PyCFunction = cts.gettype('PyCFunction')
PyCFunctionFast = cts.gettype('_PyCFunctionFast')
PyCFunctionKwArgs = cts.gettype('PyCFunctionWithKeywords')
PyCFunctionKwArgsFast = cts.gettype('_PyCFunctionFastWithKeywords')
PyCMethod = cts.gettype('PyCMethod')
PyCFunctionObject = cts.gettype('PyCFunctionObject*')
PyCMethodObject = cts.gettype('PyCMethodObject*')
TypedMethodMetadata = cts.gettype('PyPyTypedMethodMetadata')

eci = ExternalCompilationInfo(
    includes = ['Python.h', 'assert.h'],
    include_dirs = include_dirs,
    post_include_bits = [
        "RPY_EXTERN\n"
        "PyPyTypedMethodMetadata* PyPyGetTypedSignature(PyMethodDef*);"
        ],
    # TODO(max): Do this in RPython to avoid C call
    separate_module_sources = ['''
PyPyTypedMethodMetadata*
PyPyGetTypedSignature(PyMethodDef* def)
{
  assert(def->ml_flags & METH_TYPED);
  return (PyPyTypedMethodMetadata*)(def->ml_name - offsetof(PyPyTypedMethodMetadata, ml_name));
}
    '''],
)

pypy_get_typed_signature = rffi.llexternal(
    "PyPyGetTypedSignature",
    [lltype.Ptr(PyMethodDef)],
    lltype.Ptr(TypedMethodMetadata),
    compilation_info=eci,
    releasegil=False,
    # TODO(max): Is this true? What if the def is mutable?
    # elidable_function=True,
    # sandboxsafe=True,
    # _nowrapper=True,
)

long_to_long = lltype.Ptr(lltype.FuncType([rffi.LONG], rffi.LONG))
pyobject_long_to_long = lltype.Ptr(lltype.FuncType([PyObject, rffi.LONG], rffi.LONG))
pyobject_to_pyobject = lltype.Ptr(lltype.FuncType([PyObject], PyObject))
double_to_double = lltype.Ptr(lltype.FuncType([rffi.DOUBLE], rffi.DOUBLE))
double_double_to_double = lltype.Ptr(lltype.FuncType([rffi.DOUBLE, rffi.DOUBLE], rffi.DOUBLE))

@bootstrap_function
def init_functionobject(space):
    make_typedescr(W_PyCFunctionObject.typedef,
                   basestruct=PyCFunctionObject.TO,
                   attach=cfunction_attach,
                   dealloc=cfunction_dealloc)

@bootstrap_function
def init_methodobject(space):
    make_typedescr(W_PyCMethodObject.typedef,
                   basestruct=PyCMethodObject.TO,
                   attach=cmethod_attach,
                   dealloc=cmethod_dealloc)

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

def cmethod_attach(space, py_obj, w_obj, w_userdata=None):
    assert isinstance(w_obj, W_PyCMethodObject)
    py_func = rffi.cast(PyCFunctionObject, py_obj)
    py_func.c_m_ml = w_obj.ml
    py_func.c_m_self = make_ref(space, w_obj.w_self)
    py_func.c_m_module = make_ref(space, w_obj.w_module)
    py_meth = rffi.cast(PyCMethodObject, py_obj)
    py_meth.c_mm_class = w_obj.w_objclass

@slot_function([PyObject], lltype.Void)
def cmethod_dealloc(space, py_obj):
    py_func = rffi.cast(PyCFunctionObject, py_obj)
    decref(space, py_func.c_func)
    decref(space, py_func.c_m_module)
    py_meth = rffi.cast(PyCMethodObject, py_obj)
    decref(space, py_meth.c_mm_class)
    from pypy.module.cpyext.object import _dealloc
    _dealloc(space, py_obj)

def w_kwargs_from_args(space, __args__):
    if __args__.keyword_names_w is None:
        return None
    # CCC: we should probably have a @jit.look_inside_iff if the
    # keyword count is constant, as we do in Arguments.unpack
    w_kwargs = space.newdict()
    for i in range(len(__args__.keyword_names_w)):
        w_key = __args__.keyword_names_w[i]
        w_obj = __args__.keywords_w[i]
        space.setitem(w_kwargs, w_key, w_obj)
    return w_kwargs

def w_fastcall_args_from_args(space, __args__):
    # Similar to the above, but pack keys into a tuple and positional and
    # keyword arguments into a single tuple object (to be passed raw)
    state = space.fromcache(State)

    if __args__.keyword_names_w is not None and len(__args__.keyword_names_w) > 0:
        py_args = tuple_from_args_w(space, __args__.arguments_w + __args__.keywords_w)
        w_kwnames = space.newtuple(__args__.keyword_names_w)
    else:
        py_args = tuple_from_args_w(space, __args__.arguments_w)
        w_kwnames = None

    py_args = rffi.cast(PyTupleObject, py_args)
    return py_args, len(__args__.arguments_w), w_kwnames

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


T_C_LONG = 1
T_C_DOUBLE = 2
T_PY_OBJECT = 3


class CSig(object):
    _immutable_fields_ = ["arg_types[*]", "ret_type", "underlying_func", "can_raise", "cif_descr"]

    cif_descr = lltype.nullptr(CIF_DESCRIPTION)

    def __init__(self, space, arg_types, ret_type, underlying_func, can_raise):
        self.space = space
        self.arg_types = arg_types
        self.ret_type = ret_type
        self.underlying_func = underlying_func
        self.can_raise = can_raise
        self._build_cif_descr()

    def _build_cif_descr(self):
        from pypy.module._cffi_backend.ctypefunc import CifDescrBuilder
        fargs = [self._cffi_typ(typ) for typ in self.arg_types]
        fresult = self._cffi_typ(self.ret_type)
        abi = clibffi.FFI_DEFAULT_ABI
        builder = CifDescrBuilder(fargs, fresult, abi)
        self.cif_descr = builder.rawallocate(self.space)

    def _cffi_typ(self, typ):
        # it's a bit of a hack to use cffi types in order to be able to use
        # CifDescrBuilder. should probably be eventually be replaced
        from pypy.module._cffi_backend import ctypeobj

        space = self.space
        cffibackend = space.getbuiltinmodule('_cffi_backend')
        if typ == T_C_LONG:
            w_res = space.call_method(cffibackend, 'new_primitive_type', space.newtext('long'))
        elif typ == T_C_DOUBLE:
            w_res = space.call_method(cffibackend, 'new_primitive_type', space.newtext('double'))
        elif typ == T_PY_OBJECT:
            # void* always means PyObject* in this context
            w_res = space.call_method(cffibackend, 'new_pointer_type',
                                     space.call_method(cffibackend, 'new_void_type'))
        else:
            raise ValueError
        assert isinstance(w_res, ctypeobj.W_CType)
        return w_res

    @rgc.must_be_light_finalizer
    def __del__(self):
        if self.cif_descr:
            lltype.free(self.cif_descr, flavor='raw')

    @staticmethod
    def from_ml(space, ml):
        sig = pypy_get_typed_signature(ml)
        arg_types = []
        idx = 0
        while True:
            arg_type = intmask(sig.c_arg_types[idx])
            assert arg_type != 0
            if arg_type == -1:
                break
            arg_types.append(arg_type)
            idx += 1
        ret_type = intmask(sig.c_ret_type)
        assert ret_type != 0
        can_raise = False
        if ret_type < 0:
            ret_type = -ret_type
            can_raise = True
        try:
            return CSig(space, arg_types[:], ret_type, sig.c_underlying_func, can_raise)
        except ValueError:
            return None # TODO: right now, invalid signatures just lead to the typed path not being used


class W_PyCFunctionObject(W_Root):
    # TODO(max): Maybe add w_self as immutable field
    _immutable_fields_ = ["flags", "ml", "csig"]

    def __init__(self, space, ml, w_self, w_module=None, type_name=None):
        self.ml = ml
        self.name = rffi.charp2str(rffi.cast(rffi.CCHARP, self.ml.c_ml_name))
        # class methods have type_name
        if type_name:
            self.qualname = type_name + "." + self.name
        else:
            self.qualname = self.name
        self.flags = rffi.cast(lltype.Signed, self.ml.c_ml_flags)
        self.w_self = w_self
        self.w_module = w_module
        flags = self.flags & ~(METH_CLASS | METH_STATIC | METH_COEXIST)
        if flags & METH_TYPED:
            self.csig = CSig.from_ml(space, ml)
        else:
            self.csig = None

    def descr_call(self, space, __args__):
        return self.call(space, self.w_self, __args__)

    def call(self, space, w_self, __args__):
        flags = self.flags & ~(METH_CLASS | METH_STATIC | METH_COEXIST)
        length = len(__args__.arguments_w)
        if not flags & METH_KEYWORDS and __args__.keyword_names_w:
            raise oefmt(space.w_TypeError,
                        "%s() takes no keyword arguments", self.name)
        elif flags & METH_FASTCALL:
            if flags & METH_KEYWORDS:
                if flags & METH_METHOD:
                    return self.call_keywords_fastcall_method(space, w_self, __args__)
                return self.call_keywords_fastcall(space, w_self, __args__)
            if self.csig is not None:
                w_res = self._call_typed(space, __args__.arguments_w)
                if w_res is not None:
                    return w_res
                # otherwise use slow variant
            return self.call_varargs_fastcall(space, w_self, __args__)
        elif flags & METH_KEYWORDS:
            return self.call_keywords(space, w_self, __args__)
        elif flags & METH_NOARGS:
            if length == 0:
                return self.call_noargs(space, w_self, __args__)
            raise oefmt(space.w_TypeError,
                        "%s() takes no arguments (%d given)", self.name, length)
        elif flags & METH_O:
            if length != 1:
                raise oefmt(space.w_TypeError,
                            "%s() takes exactly one argument (%d given)",
                            self.name, length)
            if self.csig is not None:
                w_res = self._call_typed(space, __args__.arguments_w)
                if w_res is not None:
                    return w_res
                # otherwise use slow variant
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

    def call_varargs_fastcall(self, space, w_self, __args__):
        func = rffi.cast(PyCFunctionFast, self.ml.c_ml_meth)
        py_args, len_args, _ = w_fastcall_args_from_args(space, __args__)
        try:
            return generic_cpy_call(space, func, w_self,
                                    py_args.c_ob_item, len_args)
        finally:
            decref(space, py_args)

    @jit.unroll_safe
    def _call_typed(self, space, args_w):
        assert sys.maxint == 2 ** 63 - 1
        sig = self.csig
        assert sig is not None
        if len(sig.arg_types) != len(args_w):
            return None # returns None if the generic call path must be used

        cif_descr = sig.cif_descr
        size = cif_descr.exchange_size
        mustfree_max_plus_1 = 0
        buffer = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')
        try:
            for i in range(len(args_w)):
                data = rffi.ptradd(buffer, cif_descr.exchange_args[i])
                w_obj = args_w[i]
                typ = sig.arg_types[i]
                if typ == T_C_LONG:
                    value = space.int_w(w_obj)
                    rffi.cast(rffi.LONGP, data)[0] = value
                elif typ == T_C_DOUBLE:
                    if not space.isinstance_w(w_obj, space.w_float):
                        return None
                    value = space.float_w(w_obj)
                    rffi.cast(rffi.DOUBLEP, data)[0] = value
                elif typ == T_PY_OBJECT:
                    value = make_ref(space, w_obj)
                    mustfree_max_plus_1 = i + 1
                    rffi.cast(PyObjectP, data)[0] = value

            jit_ffi_call(cif_descr,
                         rffi.cast(rffi.VOIDP, sig.underlying_func),
                         buffer)

            resultdata = rffi.ptradd(buffer, cif_descr.exchange_result)
            typ = sig.ret_type
            if typ == T_C_LONG:
                value = rffi.cast(rffi.LONGP, resultdata)[0]
                if sig.can_raise and value == -1:
                    state = space.fromcache(State)
                    state.check_and_raise_exception(always=True)
                w_res = space.newint(value)
            elif typ == T_C_DOUBLE:
                value = rffi.cast(rffi.DOUBLEP, resultdata)[0]
                if sig.can_raise and value == -0.0: # TODO fix comparison
                    state = space.fromcache(State)
                    state.check_and_raise_exception(always=True)
                w_res = space.newfloat(value)
            elif typ == T_PY_OBJECT:
                ptrdata = rffi.cast(PyObjectP, resultdata)[0]
                if sig.can_raise and not ptrdata:  # if == NULL
                    state = space.fromcache(State)
                    state.check_and_raise_exception(always=True)
                w_res = get_w_obj_and_decref(space, ptrdata)
            else:
                assert 0, "should be unreachable"

        finally:
            for i in range(mustfree_max_plus_1):
                typ = sig.arg_types[i]
                if typ == T_PY_OBJECT:
                    data = rffi.ptradd(buffer, cif_descr.exchange_args[i])
                    decref(space, rffi.cast(PyObjectP, data)[0])
            lltype.free(buffer, flavor='raw')
            keepalive_until_here(args_w)
        return w_res

    def call_keywords(self, space, w_self, __args__):
        func = rffi.cast(PyCFunctionKwArgs, self.ml.c_ml_meth)
        py_args = tuple_from_args_w(space, __args__.arguments_w)
        w_kwargs = w_kwargs_from_args(space, __args__)
        try:
            return generic_cpy_call(space, func, w_self, py_args, w_kwargs)
        finally:
            decref(space, py_args)

    def call_keywords_fastcall(self, space, w_self, __args__):
        func = rffi.cast(PyCFunctionKwArgsFast, self.ml.c_ml_meth)
        py_args, len_args, w_kwnames = w_fastcall_args_from_args(space, __args__)
        try:
            return generic_cpy_call(space, func, w_self,
                                    py_args.c_ob_item, len_args, w_kwnames)
        finally:
            decref(space, py_args)

    def call_keywords_fastcall_method(self, space, w_self, __args__):
        func = rffi.cast(PyCMethod, self.ml.c_ml_meth)
        py_args, len_args, w_kwnames = w_fastcall_args_from_args(space, __args__)
        try:
            # Signature is (PyObject *, PyTypeObject*, PyObject ** args, size_t nargs, PyObject*kwnames)
            py_type = cts.cast("PyTypeObject*", make_ref(space, self.w_objclass))
            return generic_cpy_call(space, func, w_self, py_type, py_args.c_ob_item,
                                    rffi.cast(rffi.SIZE_T, len_args), w_kwnames)
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

    def fget_module(self, space):
        if self.w_module is None:
            return space.w_None
        return self.w_module

    def fset_module(self, space, w_module):
        self.w_module = w_module

    def fdel_module(self, space):
        self.w_module = space.w_None

class W_PyCMethodObject(W_PyCFunctionObject):

    def __init__(self, space, ml, w_self, w_module, w_type, type_name):
        W_PyCFunctionObject.__init__(self, space, ml, w_self, w_module, type_name)
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

    def __init__(self, space, ml, w_type, type_name):
        W_PyCFunctionObject.__init__(self, space, ml, w_self=None, type_name=type_name)
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
            self.space, "built-in method '%s' of '%s' object" %
            (self.name, self.w_objclass.getname(self.space)))


class W_PyCWrapperObject(W_Root):
    """
    Abstract class; for concrete subclasses, see slotdefs.py
    """
    def __init__(self, space, w_type, method_name, doc, func, type_name):
        # When this is called, w_type is only partially constructed so we
        # get its name via type_name
        self.space = space
        self.method_name = method_name
        self.doc = doc
        self.func = func
        assert isinstance(w_type, W_TypeObject)
        self.w_objclass = w_type
        self.qualname = type_name + "." + method_name

    def descr_call(self, space, w_self, __args__):
        return self.call(space, w_self, __args__)

    def call(self, space, w_self, __args__):
        raise NotImplementedError

    def get_func_to_call(self):
        return self.func

    def check_args(self, __args__, arity):
        length = len(__args__.arguments_w)
        if length != arity:
            raise oefmt(self.space.w_TypeError, "expected %d arguments, got %d",
                        arity, length)
        if __args__.keyword_names_w:
            raise oefmt(self.space.w_TypeError,
                        "wrapper %s doesn't take any keyword arguments",
                        self.method_name)

    def check_argsv(self, __args__, min, max):
        length = len(__args__.arguments_w)
        if not min <= length <= max:
            raise oefmt(self.space.w_TypeError, "expected %d-%d arguments, got %d",
                        min, max, length)
        if __args__.keyword_names_w:
            raise oefmt(self.space.w_TypeError,
                        "wrapper %s doesn't take any keyword arguments",
                        self.method_name)

    def descr_method_repr(self):
        return self.space.newtext("<slot wrapper '%s' of '%s' objects>" %
                                  (self.method_name,
                                   self.w_objclass.name))

    def descr_get_doc(self, space):
        py_obj = make_ref(space, self)
        py_methoddescr = cts.cast('PyWrapperDescrObject*', py_obj)
        if py_methoddescr.c_d_base and py_methoddescr.c_d_base.c_doc:
            doc = rffi.constcharp2str(py_methoddescr.c_d_base.c_doc)
        else:
            doc = self.doc
        if doc:
            return space.newtext(doc)
        return space.w_None

class CMethod(_Method):
    # Differentiate this from an app-level class Method
    # so isinstance(c-class-meth, type(app-class-method)) is False
    def descr_method__new__(space, w_subtype, w_function, w_instance):
        if space.is_w(w_instance, space.w_None):
            w_instance = None
        if w_instance is None:
            raise oefmt(space.w_TypeError, "self must not be None")
        method = space.allocate_instance(CMethod, w_subtype)
        _Method.__init__(method, space, w_function, w_instance)
        return method

    pass

CMethod.typedef = TypeDef(
    "builtin method",
    __doc__ = """instancemethod(function, instance, class)

Create an instance method object.""",
    __new__ = interp2app(CMethod.descr_method__new__.im_func),
    __call__ = interp2app(CMethod.descr_method_call),
    __get__ = interp2app(CMethod.descr_method_get),
    __func__ = interp_attrproperty_w('w_function', cls=CMethod),
    __self__ = interp_attrproperty_w('w_instance', cls=CMethod),
    __getattribute__ = interp2app(CMethod.descr_method_getattribute),
    __eq__ = interp2app(CMethod.descr_method_eq),
    __ne__ = descr_generic_ne,
    __hash__ = interp2app(CMethod.descr_method_hash),
    __repr__ = interp2app(CMethod.descr_method_repr),
    __reduce__ = interp2app(CMethod.descr_method__reduce__),
    __weakref__ = make_weakref_descr(CMethod),
    )
CMethod.typedef.acceptable_as_base_class = False


def cmethod_descr_get(space, w_function, w_obj, w_cls=None):
    if w_obj is None or space.is_w(w_obj, space.w_None):
        return w_function
    else:
        return CMethod(space, w_function, w_obj)

def cclassmethod_descr_get(space, w_function, w_obj, w_cls=None):
    if not w_cls:
        w_cls = space.type(w_obj)
    return CMethod(space, w_function, w_cls)


W_PyCFunctionObject.typedef = TypeDef(
    'builtin_function_or_method',
    __call__ = interp2app(W_PyCFunctionObject.descr_call),
    __doc__ = GetSetProperty(W_PyCFunctionObject.get_doc),
    __text_signature__ = GetSetProperty(W_PyCFunctionObject.get_txtsig),
    __module__ = GetSetProperty(W_PyCFunctionObject.fget_module,
                                W_PyCFunctionObject.fset_module,
                                W_PyCFunctionObject.fdel_module),
    __name__ = interp_attrproperty('name', cls=W_PyCFunctionObject,
        wrapfn="newtext_or_none"),
    __qualname__ = interp_attrproperty('qualname', cls=W_PyCFunctionObject,
        wrapfn="newtext_or_none"),
    )
W_PyCFunctionObject.typedef.acceptable_as_base_class = False

W_PyCMethodObject.typedef = TypeDef(
    'method_descriptor',
    __get__ = interp2app(cmethod_descr_get),
    __call__ = interp2app(W_PyCMethodObject.descr_call),
    __name__ = interp_attrproperty('name', cls=W_PyCMethodObject,
        wrapfn="newtext_or_none"),
    __qualname__ = interp_attrproperty('qualname', cls=W_PyCMethodObject,
        wrapfn="newtext_or_none"),
    __objclass__ = interp_attrproperty_w('w_objclass', cls=W_PyCMethodObject),
    __repr__ = interp2app(W_PyCMethodObject.descr_method_repr),
    )
W_PyCMethodObject.typedef.acceptable_as_base_class = False

W_PyCClassMethodObject.typedef = TypeDef(
    'builtin_function_or_method',
    __get__ = interp2app(cclassmethod_descr_get),
    __call__ = interp2app(W_PyCClassMethodObject.descr_call),
    __name__ = interp_attrproperty('name', cls=W_PyCClassMethodObject,
        wrapfn="newtext_or_none"),
    __qualname__ = interp_attrproperty('qualname', cls=W_PyCClassMethodObject,
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
    __qualname__ = interp_attrproperty('qualname', cls=W_PyCWrapperObject,
        wrapfn="newtext_or_none"),
    __doc__ = GetSetProperty(W_PyCWrapperObject.descr_get_doc),
    __objclass__ = interp_attrproperty_w('w_objclass', cls=W_PyCWrapperObject),
    __repr__ = interp2app(W_PyCWrapperObject.descr_method_repr),
    # XXX missing: __getattribute__
    )
W_PyCWrapperObject.typedef.acceptable_as_base_class = False


@cpython_api([lltype.Ptr(PyMethodDef), PyObject, PyObject, PyObject], PyObject)
def PyCMethod_New(space, ml, w_self, w_name, w_type):
    flags = rffi.cast(lltype.Signed, ml.c_ml_flags)
    if flags & METH_METHOD:
        if w_type is None:
            raise oefmt(space.w_SystemError,
                "attempting to create PyCMethod with a METH_METHOD "
                "flag but no class");
        if not isinstance(w_type, W_TypeObject):
            raise oefmt(space.w_SystemError,
                        "bad argument to PyCMethod_New")
        assert isinstance(w_type, W_TypeObject)
        return W_PyCMethodObject(space, ml, w_self, w_name, w_type, w_type.qualname)
    else:
        if w_type:
            raise oefmt(space.w_SystemError,
                "attempting to create PyCFunction with class "
                "but no METH_METHOD flag");
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
    PyDescr_NewMethod(PyTypeObject *type, PyMethodDef *method)""")
def PyDescr_NewMethod(space, w_type, method):
    return W_PyCMethodObject(space, method, None, None, w_type, None)

@cts.decl("""
    PyObject *
    PyDescr_NewClassMethod(PyTypeObject *type, PyMethodDef *method)""")
def PyDescr_NewClassMethod(space, w_type, method):
    if not isinstance(w_type, W_TypeObject):
        raise oefmt(space.w_SystemError,
                    "bad argument to PyDescr_NewClassMethod")
    assert isinstance(w_type, W_TypeObject)
    return W_PyCClassMethodObject(space, method, w_type, w_type.qualname)

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

def argtuple_from_pyobject_array(space, py_args, n):
    args_w = [None] * n
    for i in range(n):
        args_w[i] = from_ref(space, py_args[i])
    return space.newtuple(args_w)

def obj_and_tuple_from_pyobject_array(space, py_args, n_minus_1):
    args_w = [None] * n_minus_1
    for i in range(n_minus_1):
        args_w[i] = from_ref(space, py_args[i + 1])
    return from_ref(space, py_args[0]), args_w

def PyVectorcall_NARGS(n):
    PY_VECTORCALL_ARGUMENTS_OFFSET = 1 << (8 * rffi.sizeof(rffi.SIZE_T) - 1)
    return n & ~PY_VECTORCALL_ARGUMENTS_OFFSET

@cts.decl("PyObject *PyObject_Vectorcall(PyObject *, PyObject *const *, "
          "size_t, PyObject *)")
def PyObject_Vectorcall(space, w_func, py_args, n, w_argnames):

    if w_argnames is None:
        n_kwargs = -1
    else:
        n_kwargs = space.len_w(w_argnames)
    n = PyVectorcall_NARGS(n)
    w_args = argtuple_from_pyobject_array(space, py_args, n)
    if w_argnames is None:
        w_kwargs = None
    else:
        w_kwargs = space.newdict()
        for i in range(n_kwargs):
            space.setitem(w_kwargs, space.getitem(w_argnames, space.newint(i)),
                    from_ref(space, py_args[n + i]))
    w_result = space.call(w_func, w_args, w_kwargs)
    return w_result

@cts.decl("PyObject *_PyObject_FastCall(PyObject *, PyObject *const *, "
          "size_t)")
def _PyObject_FastCall(space, w_func, py_args, n):
    return PyObject_Vectorcall(space, w_func, py_args, n, lltype.nullptr(PyObject.TO))

@cts.decl("PyObject *PyObject_VectorcallDict(PyObject *, PyObject *const *, "
          "size_t, PyObject *)")
def PyObject_VectorcallDict(space, w_func, py_args, n, w_kwargs):
    w_args = argtuple_from_pyobject_array(space, py_args, n)
    w_result = space.call(w_func, w_args, w_kwargs)
    return w_result

@cts.decl("PyObject *PyObject_VectorcallMethod(PyObject *, PyObject *const *, "
          "size_t, PyObject *)")
def PyObject_VectorcallMethod(space, w_name, py_args, n, w_argnames):
    if w_argnames is None:
        n_kwargs = -1
    else:
        n_kwargs = space.len_w(w_argnames)
    n = PyVectorcall_NARGS(n)
    n_minus_1 = n - 1
    if n_minus_1 < 0:
        raise oefmt(space.w_ValueError, "n<1 in call to PyObject_VectorcallMethod")
    w_obj, args_w = obj_and_tuple_from_pyobject_array(space, py_args, n_minus_1)
    if w_argnames is None:
        # fast path. Cannot use call_method(... *args_w)
        name = space.text_w(w_name)
        if n_minus_1 == 0:
            return space.call_method(w_obj, name)
        elif n_minus_1 == 1:
            return space.call_method(w_obj, name, args_w[0])
        elif n_minus_1 == 2:
            return space.call_method(w_obj, name, args_w[0], args_w[1])
        elif n_minus_1 == 3:
            return space.call_method(w_obj, name, args_w[0], args_w[1], args_w[2])
        w_meth = space.getattr(w_obj, w_name)
        return space.call(w_meth, space.newtuple(args_w))
    w_kwargs = space.newdict()
    for i in range(n_kwargs):
        space.setitem(w_kwargs, space.getitem(w_argnames, space.newint(i)),
                from_ref(space, py_args[n + i]))
    w_meth = space.getattr(w_obj, w_name)
    return space.call(w_meth, space.newtuple(args_w), w_kwargs)


