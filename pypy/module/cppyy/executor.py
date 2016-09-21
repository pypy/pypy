import sys

from pypy.interpreter.error import oefmt

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import jit_libffi

from pypy.module._rawffi.interp_rawffi import unpack_simple_shape
from pypy.module._rawffi.array import W_Array, W_ArrayInstance

from pypy.module.cppyy import helper, capi, ffitypes

# Executor objects are used to dispatch C++ methods. They are defined by their
# return type only: arguments are converted by Converter objects, and Executors
# only deal with arrays of memory that are either passed to a stub or libffi.
# No argument checking or conversions are done.
#
# If a libffi function is not implemented, FastCallNotPossible is raised. If a
# stub function is missing (e.g. if no reflection info is available for the
# return type), an app-level TypeError is raised.
#
# Executor instances are created by get_executor(<return type name>), see
# below. The name given should be qualified in case there is a specialised,
# exact match for the qualified type.


NULL = lltype.nullptr(jit_libffi.FFI_TYPE_P.TO)

class FunctionExecutor(object):
    _immutable_fields_ = ['libffitype']

    libffitype = NULL

    def __init__(self, space, extra):
        pass

    def execute(self, space, cppmethod, cppthis, num_args, args):
        raise oefmt(space.w_TypeError,
                    "return type not available or supported")

    def execute_libffi(self, space, cif_descr, funcaddr, buffer):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible


class PtrTypeExecutor(FunctionExecutor):
    _immutable_fields_ = ['libffitype', 'typecode']

    libffitype = jit_libffi.types.pointer
    typecode = 'P'

    def execute(self, space, cppmethod, cppthis, num_args, args):
        if hasattr(space, "fake"):
            raise NotImplementedError
        lresult = capi.c_call_l(space, cppmethod, cppthis, num_args, args)
        ptrval = rffi.cast(rffi.ULONG, lresult)
        arr = space.interp_w(W_Array, unpack_simple_shape(space, space.wrap(self.typecode)))
        if ptrval == 0:
            from pypy.module.cppyy import interp_cppyy
            return interp_cppyy.get_nullptr(space)
        return arr.fromaddress(space, ptrval, sys.maxint)


class VoidExecutor(FunctionExecutor):
    _immutable_fields_ = ['libffitype']

    libffitype = jit_libffi.types.void

    def execute(self, space, cppmethod, cppthis, num_args, args):
        capi.c_call_v(space, cppmethod, cppthis, num_args, args)
        return space.w_None

    def execute_libffi(self, space, cif_descr, funcaddr, buffer):
        jit_libffi.jit_ffi_call(cif_descr, funcaddr, buffer)
        return space.w_None


class NumericExecutorMixin(object):
    _mixin_ = True

    def _wrap_object(self, space, obj):
        return space.wrap(obj)

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = self.c_stubcall(space, cppmethod, cppthis, num_args, args)
        return self._wrap_object(space, rffi.cast(self.c_type, result))

    def execute_libffi(self, space, cif_descr, funcaddr, buffer):
        jit_libffi.jit_ffi_call(cif_descr, funcaddr, buffer)
        result = rffi.ptradd(buffer, cif_descr.exchange_result)
        return self._wrap_object(space, rffi.cast(self.c_ptrtype, result)[0])

class NumericRefExecutorMixin(object):
    _mixin_ = True

    def __init__(self, space, extra):
        FunctionExecutor.__init__(self, space, extra)
        self.do_assign = False
        self.item = rffi.cast(self.c_type, 0)

    def set_item(self, space, w_item):
        self.item = self._unwrap_object(space, w_item)
        self.do_assign = True

    def _wrap_object(self, space, obj):
        return space.wrap(rffi.cast(self.c_type, obj))

    def _wrap_reference(self, space, rffiptr):
        if self.do_assign:
            rffiptr[0] = self.item
        self.do_assign = False
        return self._wrap_object(space, rffiptr[0])    # all paths, for rtyper

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = capi.c_call_r(space, cppmethod, cppthis, num_args, args)
        return self._wrap_reference(space, rffi.cast(self.c_ptrtype, result))

    def execute_libffi(self, space, cif_descr, funcaddr, buffer):
        jit_libffi.jit_ffi_call(cif_descr, funcaddr, buffer)
        result = rffi.ptradd(buffer, cif_descr.exchange_result)
        return self._wrap_reference(space,
            rffi.cast(self.c_ptrtype, rffi.cast(rffi.VOIDPP, result)[0]))


class CStringExecutor(FunctionExecutor):

    def execute(self, space, cppmethod, cppthis, num_args, args):
        lresult = capi.c_call_l(space, cppmethod, cppthis, num_args, args)
        ccpresult = rffi.cast(rffi.CCHARP, lresult)
        if ccpresult == rffi.cast(rffi.CCHARP, 0):
            return space.wrap("")
        result = rffi.charp2str(ccpresult)   # TODO: make it a choice to free
        return space.wrap(result)


class ConstructorExecutor(FunctionExecutor):

    def execute(self, space, cppmethod, cpptype, num_args, args):
        from pypy.module.cppyy import interp_cppyy
        newthis = capi.c_constructor(space, cppmethod, cpptype, num_args, args)
        assert lltype.typeOf(newthis) == capi.C_OBJECT
        return space.wrap(rffi.cast(rffi.LONG, newthis))   # really want ptrdiff_t here


class InstancePtrExecutor(FunctionExecutor):
    _immutable_fields_ = ['libffitype', 'cppclass']

    libffitype = jit_libffi.types.pointer

    def __init__(self, space, cppclass):
        FunctionExecutor.__init__(self, space, cppclass)
        self.cppclass = cppclass

    def execute(self, space, cppmethod, cppthis, num_args, args):
        from pypy.module.cppyy import interp_cppyy
        long_result = capi.c_call_l(space, cppmethod, cppthis, num_args, args)
        ptr_result = rffi.cast(capi.C_OBJECT, long_result)
        pyres = interp_cppyy.wrap_cppobject(space, ptr_result, self.cppclass)
        return pyres

    def execute_libffi(self, space, cif_descr, funcaddr, buffer):
        jit_libffi.jit_ffi_call(cif_descr, funcaddr, buffer)
        result = rffi.ptradd(buffer, cif_descr.exchange_result)
        from pypy.module.cppyy import interp_cppyy
        ptr_result = rffi.cast(capi.C_OBJECT, rffi.cast(rffi.VOIDPP, result)[0])
        return interp_cppyy.wrap_cppobject(space, ptr_result, self.cppclass)

class InstancePtrPtrExecutor(InstancePtrExecutor):

    def execute(self, space, cppmethod, cppthis, num_args, args):
        from pypy.module.cppyy import interp_cppyy
        voidp_result = capi.c_call_r(space, cppmethod, cppthis, num_args, args)
        ref_address = rffi.cast(rffi.VOIDPP, voidp_result)
        ptr_result = rffi.cast(capi.C_OBJECT, ref_address[0])
        return interp_cppyy.wrap_cppobject(space, ptr_result, self.cppclass)

    def execute_libffi(self, space, cif_descr, funcaddr, buffer):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible

class InstanceExecutor(InstancePtrExecutor):

    def execute(self, space, cppmethod, cppthis, num_args, args):
        from pypy.module.cppyy import interp_cppyy
        long_result = capi.c_call_o(space, cppmethod, cppthis, num_args, args, self.cppclass)
        ptr_result = rffi.cast(capi.C_OBJECT, long_result)
        return interp_cppyy.wrap_cppobject(space, ptr_result, self.cppclass,
                                           do_cast=False, python_owns=True, fresh=True)

    def execute_libffi(self, space, cif_descr, funcaddr, buffer):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible


class StdStringExecutor(InstancePtrExecutor):

    def execute(self, space, cppmethod, cppthis, num_args, args):
        cstr_result = capi.c_call_s(space, cppmethod, cppthis, num_args, args)
        return space.wrap(capi.charp2str_free(space, cstr_result))

    def execute_libffi(self, space, cif_descr, funcaddr, buffer):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible

class StdStringRefExecutor(InstancePtrExecutor):

    def __init__(self, space, cppclass):
        from pypy.module.cppyy import interp_cppyy
        cppclass = interp_cppyy.scope_byname(space, capi.std_string_name)
        InstancePtrExecutor.__init__(self, space, cppclass)


class PyObjectExecutor(PtrTypeExecutor):

    def wrap_result(self, space, lresult):
        space.getbuiltinmodule("cpyext")
        from pypy.module.cpyext.pyobject import PyObject, from_ref, make_ref, Py_DecRef
        result = rffi.cast(PyObject, lresult)
        w_obj = from_ref(space, result)
        if result:
            Py_DecRef(space, result)
        return w_obj

    def execute(self, space, cppmethod, cppthis, num_args, args):
        if hasattr(space, "fake"):
            raise NotImplementedError
        lresult = capi.c_call_l(space, cppmethod, cppthis, num_args, args)
        return self.wrap_result(space, lresult)

    def execute_libffi(self, space, cif_descr, funcaddr, buffer):
        if hasattr(space, "fake"):
            raise NotImplementedError
        jit_libffi.jit_ffi_call(cif_descr, funcaddr, buffer)
        result = rffi.ptradd(buffer, cif_descr.exchange_result)
        return self.wrap_result(space, rffi.cast(rffi.LONGP, result)[0])


_executors = {}
def get_executor(space, name):
    # Matching of 'name' to an executor factory goes through up to four levels:
    #   1) full, qualified match
    #   2) drop '&': by-ref is pretty much the same as by-value, python-wise
    #   3) types/classes, either by ref/ptr or by value
    #   4) additional special cases
    #
    # If all fails, a default is used, which can be ignored at least until use.

    name = capi.c_resolve_name(space, name)

    #   1) full, qualified match
    try:
        return _executors[name](space, None)
    except KeyError:
        pass

    compound = helper.compound(name)
    clean_name = capi.c_resolve_name(space, helper.clean_type(name))

    #   1a) clean lookup
    try:
        return _executors[clean_name+compound](space, None)
    except KeyError:
        pass

    #   2) drop '&': by-ref is pretty much the same as by-value, python-wise
    if compound and compound[len(compound)-1] == '&':
        # TODO: this does not actually work with Reflex (?)
        try:
            return _executors[clean_name](space, None)
        except KeyError:
            pass

    #   3) types/classes, either by ref/ptr or by value
    from pypy.module.cppyy import interp_cppyy
    cppclass = interp_cppyy.scope_byname(space, clean_name)
    if cppclass:
        # type check for the benefit of the annotator
        from pypy.module.cppyy.interp_cppyy import W_CPPClass
        cppclass = space.interp_w(W_CPPClass, cppclass, can_be_None=False)
        if compound == '':
            return InstanceExecutor(space, cppclass)
        elif compound == '*' or compound == '&':
            return InstancePtrExecutor(space, cppclass)
        elif compound == '**' or compound == '*&':
            return InstancePtrPtrExecutor(space, cppclass)
    elif capi.c_is_enum(space, clean_name):
        return _executors['unsigned int'](space, None)

    # 4) additional special cases
    if compound == '*':
        return _executors['void*'](space, None)  # allow at least passing of the pointer

    # currently used until proper lazy instantiation available in interp_cppyy
    return FunctionExecutor(space, None)
 

_executors["void"]                = VoidExecutor
_executors["void*"]               = PtrTypeExecutor
_executors["const char*"]         = CStringExecutor

# special cases (note: 'string' aliases added below)
_executors["constructor"]         = ConstructorExecutor

_executors["std::basic_string<char>"]         = StdStringExecutor
_executors["const std::basic_string<char>&"]  = StdStringRefExecutor
_executors["std::basic_string<char>&"]        = StdStringRefExecutor

_executors["PyObject*"]           = PyObjectExecutor

# add basic (builtin) executors
def _build_basic_executors():
    "NOT_RPYTHON"
    type_info = (
        (bool,            capi.c_call_b,   ("bool",)),
        (rffi.CHAR,       capi.c_call_c,   ("char", "unsigned char")),
        (rffi.SHORT,      capi.c_call_h,   ("short", "short int", "unsigned short", "unsigned short int")),
        (rffi.INT,        capi.c_call_i,   ("int",)),
        (rffi.UINT,       capi.c_call_l,   ("unsigned", "unsigned int")),
        (rffi.LONG,       capi.c_call_l,   ("long", "long int")),
        (rffi.ULONG,      capi.c_call_l,   ("unsigned long", "unsigned long int")),
        (rffi.LONGLONG,   capi.c_call_ll,  ("long long", "long long int")),
        (rffi.ULONGLONG,  capi.c_call_ll,  ("unsigned long long", "unsigned long long int")),
        (rffi.FLOAT,      capi.c_call_f,   ("float",)),
        (rffi.DOUBLE,     capi.c_call_d,   ("double",)),
    )

    for c_type, stub, names in type_info:
        class BasicExecutor(ffitypes.typeid(c_type), NumericExecutorMixin, FunctionExecutor):
            c_stubcall  = staticmethod(stub)
        class BasicRefExecutor(ffitypes.typeid(c_type), NumericRefExecutorMixin, FunctionExecutor):
            _immutable_fields_ = ['libffitype']
            libffitype = jit_libffi.types.pointer
        for name in names:
            _executors[name]              = BasicExecutor
            _executors[name+'&']          = BasicRefExecutor
            _executors['const '+name+'&'] = BasicRefExecutor     # no copy needed for builtins
_build_basic_executors()

# create the pointer executors; all real work is in the PtrTypeExecutor, since
# all pointer types are of the same size
def _build_ptr_executors():
    "NOT_RPYTHON"
    ptr_info = (
        ('b', ("bool",)),     # really unsigned char, but this works ...
        ('h', ("short int", "short")),
        ('H', ("unsigned short int", "unsigned short")),
        ('i', ("int",)),
        ('I', ("unsigned int", "unsigned")),
        ('l', ("long int", "long")),
        ('L', ("unsigned long int", "unsigned long")),
        ('f', ("float",)),
        ('d', ("double",)),
    )

    for tcode, names in ptr_info:
        class PtrExecutor(PtrTypeExecutor):
            _immutable_fields_ = ['typecode']
            typecode = tcode
        for name in names:
            _executors[name+'*'] = PtrExecutor
_build_ptr_executors()

# add another set of aliased names
def _add_aliased_executors():
    "NOT_RPYTHON"
    aliases = (
        ("const char*",                     "char*"),

        ("std::basic_string<char>",         "string"),
        ("const std::basic_string<char>&",  "const string&"),
        ("std::basic_string<char>&",        "string&"),

        ("PyObject*",                       "_object*"),
    )

    for c_type, alias in aliases:
        _executors[alias] = _executors[c_type]
_add_aliased_executors()
