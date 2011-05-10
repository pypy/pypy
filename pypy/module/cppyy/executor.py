import sys
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib import libffi

from pypy.module._rawffi.interp_rawffi import unpack_simple_shape
from pypy.module._rawffi.array import W_Array

from pypy.module.cppyy import helper, capi


_executors = {}

class FunctionExecutor(object):
    _immutable_ = True
    libffitype = libffi.types.NULL

    def __init__(self, space, name, cpptype):
        self.name = name

    def execute(self, space, func, cppthis, num_args, args):
        raise NotImplementedError

    def execute_libffi(self, space, libffifunc, argchain):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible


class PtrTypeExecutor(FunctionExecutor):
    _immutable_ = True
    typecode = ''

    def execute(self, space, func, cppthis, num_args, args):
        lresult = capi.c_call_l(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        address = rffi.cast(rffi.UINT, lresult)
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

class LongExecutor(FunctionExecutor):
    _immutable_ = True
    libffitype = libffi.types.slong

    def execute(self, space, func, cppthis, num_args, args):
        result = capi.c_call_l(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return space.wrap(result)

    def execute_libffi(self, space, libffifunc, argchain):
        return space.wrap(libffifunc.call(argchain, lltype.Signed))

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


def get_executor(space, name):
    from pypy.module.cppyy import interp_cppyy

    try:
        return _executors[name](space, "", None)
    except KeyError:
        pass

    compound = helper.compound(name)
    clean_name = helper.clean_type(name)
    cpptype = interp_cppyy.type_byname(space, clean_name)
    if compound == "*":           
        return InstancePtrExecutor(space, cpptype.name, cpptype)

    # currently used until proper lazy instantiation available in interp_cppyy
    return FunctionExecutor(space, "", None)
 
 #  raise TypeError("no clue what %s is" % name)

_executors["void"]                = VoidExecutor
_executors["bool"]                = BoolExecutor
_executors["char"]                = CharExecutor
_executors["unsigned char"]       = CharExecutor
_executors["short int"]           = ShortExecutor
_executors["short int*"]          = ShortPtrExecutor
_executors["unsigned short int"]  = ShortExecutor
_executors["unsigned short int*"] = ShortPtrExecutor
_executors["int"]                 = LongExecutor
_executors["int*"]                = LongPtrExecutor
_executors["unsigned int"]        = LongExecutor
_executors["unsigned int*"]       = LongPtrExecutor
_executors["long int"]            = LongExecutor
_executors["long int*"]           = LongPtrExecutor
_executors["unsigned long int"]   = LongExecutor
_executors["unsigned long int*"]  = LongPtrExecutor
_executors["float"]               = FloatExecutor
_executors["float*"]              = FloatPtrExecutor
_executors["double"]              = DoubleExecutor
_executors["double*"]             = DoublePtrExecutor
_executors["char*"]               = CStringExecutor
