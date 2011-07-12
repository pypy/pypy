import sys

from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib import libffi, clibffi

from pypy.module._rawffi.interp_rawffi import unpack_simple_shape
from pypy.module._rawffi.array import W_Array

from pypy.module.cppyy import helper, capi


NULL = lltype.nullptr(clibffi.FFI_TYPE_P.TO)

class FunctionExecutor(object):
    _immutable_ = True
    libffitype = NULL

    def __init__(self, space, name, cpptype):
        self.name = name

    def execute(self, space, func, cppthis, num_args, args):
        raise NotImplementedError

    def execute_libffi(self, space, libffifunc, argchain):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible


class PtrTypeExecutor(FunctionExecutor):
    _immutable_ = True
    typecode = 'P'

    def execute(self, space, func, cppthis, num_args, args):
        lresult = capi.c_call_l(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        address = rffi.cast(rffi.ULONG, lresult)
        arr = space.interp_w(W_Array, unpack_simple_shape(space, space.wrap(self.typecode)))
        return arr.fromaddress(space, address, sys.maxint)


class VoidExecutor(FunctionExecutor):
    _immutable_ = True

    def execute(self, space, func, cppthis, num_args, args):
        capi.c_call_v(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return space.w_None

    def execute_libffi(self, space, libffifunc, argchain):
        libffifunc.call(argchain, lltype.Void)
        return space.w_None


class BoolExecutor(FunctionExecutor):
    _immutable_ = True

    def execute(self, space, func, cppthis, num_args, args):
        result = capi.c_call_b(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return space.wrap(result)

class CharExecutor(FunctionExecutor):
    _immutable_ = True

    def execute(self, space, func, cppthis, num_args, args):
        result = capi.c_call_c(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return space.wrap(result)

class ShortExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.sshort

    def execute(self, space, func, cppthis, num_args, args):
        result = capi.c_call_h(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return space.wrap(result)

class IntExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.sint

    def _wrap_result(self, space, result):
        return space.wrap(result)

    def execute(self, space, func, cppthis, num_args, args):
        result = capi.c_call_i(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return self._wrap_result(space, result)

# TODO: check whether the following is correct (return type cast):
#   def execute_libffi(self, space, libffifunc, argchain):
#       return space.wrap(libffifunc.call(argchain, rffi.INT))

class UnsignedIntExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.uint

    def _wrap_result(self, space, result):
        return space.wrap(result)

    def execute(self, space, func, cppthis, num_args, args):
        result = capi.c_call_i(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return self._wrap_result(space, result)

class LongExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.slong

    def _wrap_result(self, space, result):
        return space.wrap(result)

    def execute(self, space, func, cppthis, num_args, args):
        result = capi.c_call_l(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return self._wrap_result(space, result)

    def execute_libffi(self, space, libffifunc, argchain):
        return space.wrap(libffifunc.call(argchain, lltype.Signed))

class ConstIntRefExecutor(LongExecutor):
    _immutable_ = True

    def _wrap_result(self, space, result):
        intptr = rffi.cast(rffi.INTP, result)
        return space.wrap(intptr[0])

class ConstLongRefExecutor(LongExecutor):
    _immutable_ = True

    def _wrap_result(self, space, result):
        longptr = rffi.cast(rffi.LONGP, result)
        return space.wrap(longptr[0])

class FloatExecutor(FunctionExecutor):
    _immutable_ = True

    def execute(self, space, func, cppthis, num_args, args):
        result = capi.c_call_f(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return space.wrap(result)

class DoubleExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.double

    def execute(self, space, func, cppthis, num_args, args):
        result = capi.c_call_d(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return space.wrap(result)

    def execute_libffi(self, space, libffifunc, argchain):
        return space.wrap(libffifunc.call(argchain, rffi.DOUBLE))


class CStringExecutor(FunctionExecutor):
    _immutable_ = True
    def execute(self, space, func, cppthis, num_args, args):
        lresult = capi.c_call_l(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        ccpresult = rffi.cast(rffi.CCHARP, lresult)
        result = capi.charp2str_free(ccpresult)
        return space.wrap(result)


class ShortPtrExecutor(PtrTypeExecutor):
    _immutable_ = True
    typecode = 'h'

class IntPtrExecutor(PtrTypeExecutor):
    _immutable_ = True
    typecode = 'i'

class UnsignedIntPtrExecutor(PtrTypeExecutor):
    _immutable_ = True
    typecode = 'I'

class LongPtrExecutor(PtrTypeExecutor):
    _immutable_ = True
    typecode = 'l'

class FloatPtrExecutor(PtrTypeExecutor):
    _immutable_ = True
    typecode = 'f'

class DoublePtrExecutor(PtrTypeExecutor):
    _immutable_ = True
    typecode = 'd'


class InstancePtrExecutor(FunctionExecutor):
    _immutable_ = True
    def __init__(self, space, name, cpptype):
        FunctionExecutor.__init__(self, space, name, cpptype)
        self.cpptype = cpptype

    def execute(self, space, func, cppthis, num_args, args):
        from pypy.module.cppyy import interp_cppyy
        long_result = capi.c_call_l(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        ptr_result = rffi.cast(rffi.VOIDP, long_result)
        return interp_cppyy.W_CPPInstance(space, self.cpptype, ptr_result)

class InstanceExecutor(InstancePtrExecutor):
    _immutable_ = True

    def execute(self, space, func, cppthis, num_args, args):
        from pypy.module.cppyy import interp_cppyy
        long_result = capi.c_call_o(
            func.cpptype.handle, func.method_index, cppthis, num_args, args, self.cpptype.handle)
        ptr_result = rffi.cast(rffi.VOIDP, long_result)
        # TODO: take ownership of result ...
        return interp_cppyy.W_CPPInstance(space, self.cpptype, ptr_result)


_executors = {}
def get_executor(space, name):
    # Matching of 'name' to an executor factory goes through up to four levels:
    #   1) full, qualified match
    #   2) drop '&': by-ref is pretty much the same as by-value, python-wise
    #   3) types/classes, either by ref/ptr or by value
    #   4) additional special cases
    #
    # If all fails, a default is used, which can be ignored at least until use.

    from pypy.module.cppyy import interp_cppyy

    #   1) full, qualified match
    try:
        return _executors[name](space, "", None)
    except KeyError:
        pass

    compound = helper.compound(name)
    clean_name = helper.clean_type(name)

    #   1a) clean lookup
    try:
        return _executors[clean_name+compound](space, "", None)
    except KeyError:
        pass

    #   2) drop '&': by-ref is pretty much the same as by-value, python-wise
    if compound and compound[len(compound)-1] == "&":
        # TODO: this does not actually work with Reflex (?)
        try:
            return _executors[clean_name](space, "", None)
        except KeyError:
            pass

    #   3) types/classes, either by ref/ptr or by value
    cpptype = interp_cppyy.type_byname(space, clean_name)
    if cpptype:
        # type check for the benefit of the annotator
        from pypy.module.cppyy.interp_cppyy import W_CPPType
        cpptype = space.interp_w(W_CPPType, cpptype, can_be_None=False)
        if compound == "*" or compound == "&":
            return InstancePtrExecutor(space, clean_name, cpptype)
        elif compound == "":
            return InstanceExecutor(space, clean_name, cpptype)

    # 4) additional special cases
    # ... none for now

    # currently used until proper lazy instantiation available in interp_cppyy
    return FunctionExecutor(space, "", None)
 
 #  raise TypeError("no clue what %s is" % name)

_executors["void"]                = VoidExecutor
_executors["void*"]               = PtrTypeExecutor
_executors["bool"]                = BoolExecutor
_executors["char"]                = CharExecutor
_executors["char*"]               = CStringExecutor
_executors["unsigned char"]       = CharExecutor
_executors["short int"]           = ShortExecutor
_executors["short int*"]          = ShortPtrExecutor
_executors["unsigned short int"]  = ShortExecutor
_executors["unsigned short int*"] = ShortPtrExecutor
_executors["int"]                 = IntExecutor
_executors["int*"]                = IntPtrExecutor
_executors["const int&"]          = ConstIntRefExecutor
_executors["int&"]                = ConstIntRefExecutor
_executors["unsigned int"]        = UnsignedIntExecutor
_executors["unsigned int*"]       = UnsignedIntPtrExecutor
_executors["long int"]            = LongExecutor
_executors["long int*"]           = LongPtrExecutor
_executors["unsigned long int"]   = LongExecutor
_executors["unsigned long int*"]  = LongPtrExecutor
_executors["float"]               = FloatExecutor
_executors["float*"]              = FloatPtrExecutor
_executors["double"]              = DoubleExecutor
_executors["double*"]             = DoublePtrExecutor
