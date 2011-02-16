import sys
from pypy.interpreter.baseobjspace import Wrappable, Arguments
from pypy.interpreter.error import OperationError, wrap_oserror, \
    operationerrfmt
from pypy.interpreter.gateway import interp2app, NoneNotWrapped, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
#
from pypy.rpython.lltypesystem import lltype, rffi
#
from pypy.rlib import jit
from pypy.rlib import libffi
from pypy.rlib.rdynload import DLOpenError
from pypy.rlib.rarithmetic import intmask

class W_FFIType(Wrappable):
    def __init__(self, name, ffitype):
        self.name = name
        self.ffitype = ffitype

    def str(self, space):
        return space.wrap('<ffi type %s>' % self.name)



W_FFIType.typedef = TypeDef(
    'FFIType',
    __str__ = interp2app(W_FFIType.str),
    )


class W_types(Wrappable):
    pass

def build_ffi_types():
    from pypy.rlib.clibffi import FFI_TYPE_P
    tdict = {}
    for key, value in libffi.types.__dict__.iteritems():
        if key == 'getkind' or key.startswith('__'):
            continue
        assert lltype.typeOf(value) == FFI_TYPE_P
        tdict[key] = W_FFIType(key, value)
    return tdict
    
W_types.typedef = TypeDef(
    'types',
    **build_ffi_types())

# ========================================================================

class W_FuncPtr(Wrappable):

    _immutable_fields_ = ['func']
    
    def __init__(self, func):
        self.func = func

    @jit.unroll_safe
    def build_argchain(self, space, argtypes, args_w):
        expected = len(argtypes)
        given = len(args_w)
        if given != expected:
            arg = 'arguments'
            if len(argtypes) == 1:
                arg = 'argument'
            raise operationerrfmt(space.w_TypeError,
                                  '%s() takes exactly %d %s (%d given)',
                                  self.func.name, expected, arg, given)
        #
        argchain = libffi.ArgChain()
        for i in range(expected):
            argtype = argtypes[i]
            w_arg = args_w[i]
            kind = libffi.types.getkind(argtype)
            if kind == 'i':
                argchain.arg(space.int_w(w_arg))
            elif kind == 'u':
                argchain.arg(intmask(space.uint_w(w_arg)))
            elif kind == 'f':
                argchain.arg(space.float_w(w_arg))
            else:
                assert False, "Argument kind '%s' not supported" % kind
        return argchain

    def call(self, space, args_w):
        self = jit.hint(self, promote=True)
        argchain = self.build_argchain(space, self.func.argtypes, args_w)
        reskind = libffi.types.getkind(self.func.restype)
        if reskind == 'i':
            return self._call_int(space, argchain)
        elif reskind == 'u':
            return self._call_uint(space, argchain)
        elif reskind == 'f':
            floatres = self.func.call(argchain, rffi.DOUBLE)
            return space.wrap(floatres)
        else:
            voidres = self.func.call(argchain, lltype.Void)
            assert voidres is None
            return space.w_None

    def _call_int(self, space, argchain):
        # if the declared return type of the function is smaller than LONG,
        # the result buffer may contains garbage in its higher bits.  To get
        # the correct value, and to be sure to handle the signed/unsigned case
        # correctly, we need to cast the result to the correct type.  After
        # that, we cast it back to LONG, because this is what we want to pass
        # to space.wrap in order to get a nice applevel <int>.
        #
        restype = self.func.restype
        call = self.func.call
        if restype is libffi.types.slong:
            intres = call(argchain, rffi.LONG)
        elif restype is libffi.types.sint:
            intres = rffi.cast(rffi.LONG, call(argchain, rffi.INT))
        elif restype is libffi.types.sshort:
            intres = rffi.cast(rffi.LONG, call(argchain, rffi.SHORT))
        elif restype is libffi.types.schar:
            intres = rffi.cast(rffi.LONG, call(argchain, rffi.SIGNEDCHAR))
        else:
            raise OperationError(space.w_ValueError,
                                 space.wrap('Unsupported restype'))
        return space.wrap(intres)

    def _call_uint(self, space, argchain):
        # the same comment as above apply. Moreover, we need to be careful
        # when the return type is ULONG, because the value might not fit into
        # a signed LONG: this is the only case in which we cast the result to
        # something different than LONG; as a result, the applevel value will
        # be a <long>.
        #
        # Note that we check for ULONG before UINT: this is needed on 32bit
        # machines, where they are they same: if we checked for UINT before
        # ULONG, we would cast to the wrong type.  Note that this also means
        # that on 32bit the UINT case will never be entered (because it is
        # handled by the ULONG case).
        restype = self.func.restype
        call = self.func.call
        if restype is libffi.types.ulong:
            # special case
            uintres = call(argchain, rffi.ULONG)
            return space.wrap(uintres)
        elif restype is libffi.types.uint:
            intres = rffi.cast(rffi.LONG, call(argchain, rffi.UINT))
        elif restype is libffi.types.ushort:
            intres = rffi.cast(rffi.LONG, call(argchain, rffi.USHORT))
        elif restype is libffi.types.uchar:
            intres = rffi.cast(rffi.LONG, call(argchain, rffi.UCHAR))
        else:
            raise OperationError(space.w_ValueError,
                                 space.wrap('Unsupported restype'))
        return space.wrap(intres)

    def getaddr(self, space):
        """
        Return the physical address in memory of the function
        """
        return space.wrap(rffi.cast(rffi.LONG, self.func.funcsym))

W_FuncPtr.typedef = TypeDef(
    'FuncPtr',
    __call__ = interp2app(W_FuncPtr.call),
    getaddr = interp2app(W_FuncPtr.getaddr),
    )



# ========================================================================

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        try:
            self.cdll = libffi.CDLL(name)
        except DLOpenError, e:
            raise operationerrfmt(space.w_OSError, '%s: %s', name,
                                  e.msg or 'unspecified error')
        self.name = name
        self.space = space

    def ffitype(self, w_argtype, allow_void=False):
        res = self.space.interp_w(W_FFIType, w_argtype).ffitype
        if res is libffi.types.void and not allow_void:
            space = self.space
            msg = 'void is not a valid argument type'
            raise OperationError(space.w_TypeError, space.wrap(msg))
        return res

    @unwrap_spec(name=str)
    def getfunc(self, space, name, w_argtypes, w_restype):
        argtypes = [self.ffitype(w_argtype) for w_argtype in
                    space.listview(w_argtypes)]
        restype = self.ffitype(w_restype, allow_void=True)
        func = self.cdll.getpointer(name, argtypes, restype)
        return W_FuncPtr(func)


@unwrap_spec(name=str)
def descr_new_cdll(space, w_type, name):
    return space.wrap(W_CDLL(space, name))


W_CDLL.typedef = TypeDef(
    'CDLL',
    __new__     = interp2app(descr_new_cdll),
    getfunc     = interp2app(W_CDLL.getfunc),
    )

# ========================================================================
