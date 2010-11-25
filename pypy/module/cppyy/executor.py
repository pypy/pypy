from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib import libffi

from pypy.module.cppyy import helper, capi


_executors = {}

class FunctionExecutor(object):
    _immutable_ = True
    libffitype = libffi.types.NULL

    def __init__(self, space, cpptype):
        pass

    def execute(self, space, func, cppthis, num_args, args):
        raise NotImplementedError

    def execute_libffi(self, space, libffifunc, argchain):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible


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


class InstancePtrExecutor(FunctionExecutor):
    _immutable_ = True
    def __init__(self, space, cpptype):
        self.cpptype = cpptype

    def execute(self, space, func, cppthis, num_args, args):
        from pypy.module.cppyy import interp_cppyy
        long_result = capi.c_call_l(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        ptr_result = rffi.cast(rffi.VOIDP, long_result)
        return interp_cppyy.W_CPPInstance(space, self.cpptype, ptr_result)


def get_executor(space, name):
    from pypy.module.cppyy import interp_cppyy

    try:
        return _executors[name](space, None)
    except KeyError:
        pass

    compound = helper.compound(name)
    cpptype = interp_cppyy.type_byname(space, helper.clean_type(name))
    if compound == "*":           
        return InstancePtrExecutor(space, cpptype)

    # currently used until proper lazy instantiation available in interp_cppyy
    return FunctionExecutor(space, None)
 
 #  raise TypeError("no clue what %s is" % name)

_executors["void"]                = VoidExecutor
_executors["bool"]                = BoolExecutor
_executors["char"]                = CharExecutor
_executors["unsigned char"]       = CharExecutor
_executors["short int"]           = ShortExecutor
_executors["unsigned short int"]  = ShortExecutor
_executors["int"]                 = LongExecutor
_executors["unsigned int"]        = LongExecutor
_executors["long int"]            = LongExecutor
_executors["unsigned long int"]   = LongExecutor
_executors["float"]               = FloatExecutor
_executors["double"]              = DoubleExecutor
_executors["char*"]               = CStringExecutor
