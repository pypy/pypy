import sys

from pypy.interpreter.error import OperationError

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib import libffi, clibffi

from pypy.module._rawffi.interp_rawffi import unpack_simple_shape
from pypy.module._rawffi.array import W_Array

from pypy.module.cppyy import helper, capi

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


NULL = lltype.nullptr(clibffi.FFI_TYPE_P.TO)

class FunctionExecutor(object):
    _immutable_ = True
    libffitype = NULL

    def __init__(self, space, extra):
        pass

    def execute(self, space, cppmethod, cppthis, num_args, args):
        raise OperationError(space.w_TypeError,
                             space.wrap('return type not available or supported'))

    def execute_libffi(self, space, libffifunc, argchain):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible


class PtrTypeExecutor(FunctionExecutor):
    _immutable_ = True
    typecode = 'P'

    def execute(self, space, cppmethod, cppthis, num_args, args):
        if hasattr(space, "fake"):
            raise NotImplementedError
        lresult = capi.c_call_l(cppmethod, cppthis, num_args, args)
        address = rffi.cast(rffi.ULONG, lresult)
        arr = space.interp_w(W_Array, unpack_simple_shape(space, space.wrap(self.typecode)))
        return arr.fromaddress(space, address, sys.maxint)


class VoidExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.void

    def execute(self, space, cppmethod, cppthis, num_args, args):
        capi.c_call_v(cppmethod, cppthis, num_args, args)
        return space.w_None

    def execute_libffi(self, space, libffifunc, argchain):
        libffifunc.call(argchain, lltype.Void)
        return space.w_None


class BoolExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.schar

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = capi.c_call_b(cppmethod, cppthis, num_args, args)
        return space.wrap(result)

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.CHAR)
        return space.wrap(bool(ord(result)))

class CharExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.schar

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = capi.c_call_c(cppmethod, cppthis, num_args, args)
        return space.wrap(result)

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.CHAR)
        return space.wrap(result)

class ShortExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.sshort

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = capi.c_call_h(cppmethod, cppthis, num_args, args)
        return space.wrap(result)

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.SHORT)
        return space.wrap(result)

class IntExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.sint

    def _wrap_result(self, space, result):
        return space.wrap(result)

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = capi.c_call_i(cppmethod, cppthis, num_args, args)
        return self._wrap_result(space, result)

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.INT)
        return space.wrap(result)

class UnsignedIntExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.uint

    def _wrap_result(self, space, result):
        return space.wrap(rffi.cast(rffi.UINT, result))

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = capi.c_call_l(cppmethod, cppthis, num_args, args)
        return self._wrap_result(space, result)

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.UINT)
        return space.wrap(result)

class LongExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.slong

    def _wrap_result(self, space, result):
        return space.wrap(result)

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = capi.c_call_l(cppmethod, cppthis, num_args, args)
        return self._wrap_result(space, result)

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.LONG)
        return space.wrap(result)

class UnsignedLongExecutor(LongExecutor):
    _immutable_ = True
    libffitype = libffi.types.ulong

    def _wrap_result(self, space, result):
        return space.wrap(rffi.cast(rffi.ULONG, result))

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.ULONG)
        return space.wrap(result)

class LongLongExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.sint64

    def _wrap_result(self, space, result):
        return space.wrap(result)

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = capi.c_call_ll(cppmethod, cppthis, num_args, args)
        return self._wrap_result(space, result)

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.LONGLONG)
        return space.wrap(result)

class UnsignedLongLongExecutor(LongLongExecutor):
    _immutable_ = True
    libffitype = libffi.types.uint64

    def _wrap_result(self, space, result):
        return space.wrap(rffi.cast(rffi.ULONGLONG, result))

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.ULONGLONG)
        return space.wrap(result)

class ConstIntRefExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.pointer

    def _wrap_result(self, space, result):
        intptr = rffi.cast(rffi.INTP, result)
        return space.wrap(intptr[0])

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = capi.c_call_r(cppmethod, cppthis, num_args, args)
        return self._wrap_result(space, result)

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.INTP)
        return space.wrap(result[0])

class ConstLongRefExecutor(ConstIntRefExecutor):
    _immutable_ = True
    libffitype = libffi.types.pointer

    def _wrap_result(self, space, result):
        longptr = rffi.cast(rffi.LONGP, result)
        return space.wrap(longptr[0])

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.LONGP)
        return space.wrap(result[0])

class FloatExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.float

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = capi.c_call_f(cppmethod, cppthis, num_args, args)
        return space.wrap(float(result))

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.FLOAT)
        return space.wrap(float(result))

class DoubleExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.double

    def execute(self, space, cppmethod, cppthis, num_args, args):
        result = capi.c_call_d(cppmethod, cppthis, num_args, args)
        return space.wrap(result)

    def execute_libffi(self, space, libffifunc, argchain):
        result = libffifunc.call(argchain, rffi.DOUBLE)
        return space.wrap(result)


class CStringExecutor(FunctionExecutor):
    _immutable_ = True

    def execute(self, space, cppmethod, cppthis, num_args, args):
        lresult = capi.c_call_l(cppmethod, cppthis, num_args, args)
        ccpresult = rffi.cast(rffi.CCHARP, lresult)
        result = rffi.charp2str(ccpresult)  # TODO: make it a choice to free
        return space.wrap(result)


class ConstructorExecutor(VoidExecutor):
    _immutable_ = True

    def execute(self, space, cppmethod, cppthis, num_args, args):
        capi.c_constructor(cppmethod, cppthis, num_args, args)
        return space.w_None


class InstancePtrExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.pointer

    def __init__(self, space, cppclass):
        FunctionExecutor.__init__(self, space, cppclass)
        self.cppclass = cppclass

    def execute(self, space, cppmethod, cppthis, num_args, args):
        from pypy.module.cppyy import interp_cppyy
        long_result = capi.c_call_l(cppmethod, cppthis, num_args, args)
        ptr_result = rffi.cast(capi.C_OBJECT, long_result)
        return interp_cppyy.wrap_cppobject(
            space, space.w_None, self.cppclass, ptr_result, isref=False, python_owns=False)

    def execute_libffi(self, space, libffifunc, argchain):
        from pypy.module.cppyy import interp_cppyy
        ptr_result = rffi.cast(capi.C_OBJECT, libffifunc.call(argchain, rffi.VOIDP))
        return interp_cppyy.wrap_cppobject(
            space, space.w_None, self.cppclass, ptr_result, isref=False, python_owns=False)

class InstancePtrPtrExecutor(InstancePtrExecutor):
    _immutable_ = True

    def execute(self, space, cppmethod, cppthis, num_args, args):
        from pypy.module.cppyy import interp_cppyy
        voidp_result = capi.c_call_r(cppmethod, cppthis, num_args, args)
        ref_address = rffi.cast(rffi.VOIDPP, voidp_result)
        ptr_result = rffi.cast(capi.C_OBJECT, ref_address[0])
        return interp_cppyy.wrap_cppobject(
            space, space.w_None, self.cppclass, ptr_result, isref=False, python_owns=False)

    def execute_libffi(self, space, libffifunc, argchain):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible

class InstanceExecutor(InstancePtrExecutor):
    _immutable_ = True

    def execute(self, space, cppmethod, cppthis, num_args, args):
        from pypy.module.cppyy import interp_cppyy
        long_result = capi.c_call_o(cppmethod, cppthis, num_args, args, self.cppclass)
        ptr_result = rffi.cast(capi.C_OBJECT, long_result)
        return interp_cppyy.wrap_cppobject(
            space, space.w_None, self.cppclass, ptr_result, isref=False, python_owns=True)

    def execute_libffi(self, space, libffifunc, argchain):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible


class StdStringExecutor(InstancePtrExecutor):
    _immutable_ = True

    def execute(self, space, cppmethod, cppthis, num_args, args):
        charp_result = capi.c_call_s(cppmethod, cppthis, num_args, args)
        return space.wrap(capi.charp2str_free(charp_result))

    def execute_libffi(self, space, libffifunc, argchain):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible


class PyObjectExecutor(PtrTypeExecutor):
    _immutable_ = True

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
        lresult = capi.c_call_l(cppmethod, cppthis, num_args, args)
        return self.wrap_result(space, lresult)

    def execute_libffi(self, space, libffifunc, argchain):
        if hasattr(space, "fake"):
            raise NotImplementedError
        lresult = libffifunc.call(argchain, rffi.LONG)
        return self.wrap_result(space, lresult)


_executors = {}
def get_executor(space, name):
    # Matching of 'name' to an executor factory goes through up to four levels:
    #   1) full, qualified match
    #   2) drop '&': by-ref is pretty much the same as by-value, python-wise
    #   3) types/classes, either by ref/ptr or by value
    #   4) additional special cases
    #
    # If all fails, a default is used, which can be ignored at least until use.

    name = capi.c_resolve_name(name)

    #   1) full, qualified match
    try:
        return _executors[name](space, None)
    except KeyError:
        pass

    compound = helper.compound(name)
    clean_name = helper.clean_type(name)

    #   1a) clean lookup
    try:
        return _executors[clean_name+compound](space, None)
    except KeyError:
        pass

    #   2) drop '&': by-ref is pretty much the same as by-value, python-wise
    if compound and compound[len(compound)-1] == "&":
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
        if compound == "":
            return InstanceExecutor(space, cppclass)
        elif compound == "*" or compound == "&":
            return InstancePtrExecutor(space, cppclass)
        elif compound == "**" or compound == "*&":
            return InstancePtrPtrExecutor(space, cppclass)
    elif capi.c_is_enum(clean_name):
        return UnsignedIntExecutor(space, None)

    # 4) additional special cases
    # ... none for now

    # currently used until proper lazy instantiation available in interp_cppyy
    return FunctionExecutor(space, None)
 

_executors["void"]                = VoidExecutor
_executors["void*"]               = PtrTypeExecutor
_executors["bool"]                = BoolExecutor
_executors["char"]                = CharExecutor
_executors["const char*"]         = CStringExecutor
_executors["short"]               = ShortExecutor
_executors["unsigned short"]      = ShortExecutor
_executors["int"]                 = IntExecutor
_executors["const int&"]          = ConstIntRefExecutor
_executors["int&"]                = ConstIntRefExecutor
_executors["unsigned"]            = UnsignedIntExecutor
_executors["long"]                = LongExecutor
_executors["unsigned long"]       = UnsignedLongExecutor
_executors["long long"]           = LongLongExecutor
_executors["unsigned long long"]  = UnsignedLongLongExecutor
_executors["float"]               = FloatExecutor
_executors["double"]              = DoubleExecutor

_executors["constructor"]         = ConstructorExecutor

# special cases (note: CINT backend requires the simple name 'string')
_executors["std::basic_string<char>"]        = StdStringExecutor

_executors["PyObject*"]           = PyObjectExecutor

# add the set of aliased names
def _add_aliased_executors():
    "NOT_RPYTHON"
    alias_info = (
        ("char",                            ("unsigned char",)),

        ("short",                           ("short int",)),
        ("unsigned short",                  ("unsigned short int",)),
        ("unsigned",                        ("unsigned int",)),
        ("long",                            ("long int",)),
        ("unsigned long",                   ("unsigned long int",)),
        ("long long",                       ("long long int",)),
        ("unsigned long long",              ("unsigned long long int",)),

        ("const char*",                     ("char*",)),

        ("std::basic_string<char>",         ("string",)),

        ("PyObject*",                       ("_object*",)),
    )

    for info in alias_info:
        for name in info[1]:
            _executors[name] = _executors[info[0]]
_add_aliased_executors()

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

    for info in ptr_info:
        class PtrExecutor(PtrTypeExecutor):
            _immutable_ = True
            typecode = info[0]
        for name in info[1]:
            _executors[name+'*'] = PtrExecutor
_build_ptr_executors()
