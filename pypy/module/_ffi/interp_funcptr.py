from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError, wrap_oserror, \
    operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.module._rawffi.structure import W_StructureInstance, W_Structure
from pypy.module._ffi.interp_ffitype import W_FFIType
#
from pypy.rpython.lltypesystem import lltype, rffi
#
from pypy.rlib import jit
from pypy.rlib import libffi
from pypy.rlib.rdynload import DLOpenError
from pypy.rlib.rarithmetic import intmask, r_uint
from pypy.rlib.objectmodel import we_are_translated
from pypy.module._ffi.dispatcher import AbstractDispatcher


def unwrap_ffitype(space, w_argtype, allow_void=False):
    res = w_argtype.ffitype
    if res is libffi.types.void and not allow_void:
        msg = 'void is not a valid argument type'
        raise OperationError(space.w_TypeError, space.wrap(msg))
    return res


# ========================================================================

class W_FuncPtr(Wrappable):

    _immutable_fields_ = ['func', 'argtypes_w[*]', 'w_restype']

    def __init__(self, func, argtypes_w, w_restype):
        self.func = func
        self.argtypes_w = argtypes_w
        self.w_restype = w_restype
        self.to_free = []

    @jit.unroll_safe
    def build_argchain(self, space, args_w):
        expected = len(self.argtypes_w)
        given = len(args_w)
        if given != expected:
            arg = 'arguments'
            if len(self.argtypes_w) == 1:
                arg = 'argument'
            raise operationerrfmt(space.w_TypeError,
                                  '%s() takes exactly %d %s (%d given)',
                                  self.func.name, expected, arg, given)
        #
        argchain = libffi.ArgChain()
        argpusher = ArgumentPusherDispatcher(space, argchain, self.to_free)
        for i in range(expected):
            w_argtype = self.argtypes_w[i]
            w_arg = args_w[i]
            argpusher.unwrap_and_do(w_argtype, w_arg)
        return argchain

    def call(self, space, args_w):
        self = jit.promote(self)
        argchain = self.build_argchain(space, args_w)
        return self._do_call(space, argchain)

    def free_temp_buffers(self, space):
        for buf in self.to_free:
            if not we_are_translated():
                buf[0] = '\00' # invalidate the buffer, so that
                               # test_keepalive_temp_buffer can fail
            lltype.free(buf, flavor='raw')
        self.to_free = []

    def _do_call(self, space, argchain):
        w_restype = self.w_restype
        if w_restype.is_longlong():
            # note that we must check for longlong first, because either
            # is_signed or is_unsigned returns true anyway
            assert libffi.IS_32_BIT
            return self._call_longlong(space, argchain)
        elif w_restype.is_signed():
            return self._call_int(space, argchain)
        elif w_restype.is_unsigned() or w_restype.is_pointer():
            return self._call_uint(space, argchain)
        elif w_restype.is_char():
            intres = self.func.call(argchain, rffi.UCHAR)
            return space.wrap(chr(intres))
        elif w_restype.is_unichar():
            intres = self.func.call(argchain, rffi.WCHAR_T)
            return space.wrap(unichr(intres))
        elif w_restype.is_double():
            return self._call_float(space, argchain)
        elif w_restype.is_singlefloat():
            return self._call_singlefloat(space, argchain)
        elif w_restype.is_struct():
            w_datashape = w_restype.w_datashape
            assert isinstance(w_datashape, W_Structure)
            ptrval = self.func.call(argchain, rffi.ULONG, is_struct=True)
            return w_datashape.fromaddress(space, ptrval)
        elif w_restype.is_void():
            voidres = self.func.call(argchain, lltype.Void)
            assert voidres is None
            return space.w_None
        else:
            assert False, "Return value shape '%s' not supported" % w_restype

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
        elif restype is libffi.types.pointer:
            ptrres = call(argchain, rffi.VOIDP)
            uintres = rffi.cast(rffi.ULONG, ptrres)
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

    def _call_float(self, space, argchain):
        # a separate function, which can be seen by the jit or not,
        # depending on whether floats are supported
        floatres = self.func.call(argchain, rffi.DOUBLE)
        return space.wrap(floatres)

    def _call_longlong(self, space, argchain):
        # a separate function, which can be seen by the jit or not,
        # depending on whether longlongs are supported
        restype = self.func.restype
        call = self.func.call
        if restype is libffi.types.slonglong:
            llres = call(argchain, rffi.LONGLONG)
            return space.wrap(llres)
        elif restype is libffi.types.ulonglong:
            ullres = call(argchain, rffi.ULONGLONG)
            return space.wrap(ullres)
        else:
            raise OperationError(space.w_ValueError,
                                 space.wrap('Unsupported longlong restype'))

    def _call_singlefloat(self, space, argchain):
        # a separate function, which can be seen by the jit or not,
        # depending on whether singlefloats are supported
        sfres = self.func.call(argchain, rffi.FLOAT)
        return space.wrap(float(sfres))

    def getaddr(self, space):
        """
        Return the physical address in memory of the function
        """
        return space.wrap(rffi.cast(rffi.LONG, self.func.funcsym))


class ArgumentPusherDispatcher(AbstractDispatcher):
    """
    A dispatcher used by W_FuncPtr to unwrap the app-level objects into
    low-level types and push them to the argchain.
    """

    def __init__(self, space, argchain, to_free):
        AbstractDispatcher.__init__(self, space)
        self.argchain = argchain
        self.to_free = to_free

    def handle_signed(self, w_ffitype, w_obj, intval):
        self.argchain.arg(intval)

    def handle_unsigned(self, w_ffitype, w_obj, uintval):
        self.argchain.arg(uintval)

    def handle_pointer(self, w_ffitype, w_obj, intval):
        self.argchain.arg(intval)

    def handle_char(self, w_ffitype, w_obj, intval):
        self.argchain.arg(intval)

    def handle_unichar(self, w_ffitype, w_obj, intval):
        self.argchain.arg(intval)

    def handle_longlong(self, w_ffitype, w_obj, longlongval):
        self.argchain.arg(longlongval)

    def handle_char_p(self, w_ffitype, w_obj, strval):
        buf = rffi.str2charp(strval)
        self.to_free.append(rffi.cast(rffi.VOIDP, buf))
        addr = rffi.cast(rffi.ULONG, buf)
        self.argchain.arg(addr)

    def handle_unichar_p(self, w_ffitype, w_obj, unicodeval):
        buf = rffi.unicode2wcharp(unicodeval)
        self.to_free.append(rffi.cast(rffi.VOIDP, buf))
        addr = rffi.cast(rffi.ULONG, buf)
        self.argchain.arg(addr)

    def handle_float(self, w_ffitype, w_obj, floatval):
        self.argchain.arg(floatval)

    def handle_singlefloat(self, w_ffitype, w_obj, singlefloatval):
        self.argchain.arg(singlefloatval)

    def handle_struct(self, w_ffitype, w_structinstance):
        ptrval = w_structinstance.ll_buffer
        self.argchain.arg_raw(ptrval)



def unpack_argtypes(space, w_argtypes, w_restype):
    argtypes_w = [space.interp_w(W_FFIType, w_argtype)
                  for w_argtype in space.listview(w_argtypes)]
    argtypes = [unwrap_ffitype(space, w_argtype) for w_argtype in
                argtypes_w]
    w_restype = space.interp_w(W_FFIType, w_restype)
    restype = unwrap_ffitype(space, w_restype, allow_void=True)
    return argtypes_w, argtypes, w_restype, restype

@unwrap_spec(addr=r_uint, name=str)
def descr_fromaddr(space, w_cls, addr, name, w_argtypes, w_restype):
    argtypes_w, argtypes, w_restype, restype = unpack_argtypes(space,
                                                               w_argtypes,
                                                               w_restype)
    addr = rffi.cast(rffi.VOIDP, addr)
    func = libffi.Func(name, argtypes, restype, addr)
    return W_FuncPtr(func, argtypes_w, w_restype)


W_FuncPtr.typedef = TypeDef(
    '_ffi.FuncPtr',
    __call__ = interp2app(W_FuncPtr.call),
    getaddr = interp2app(W_FuncPtr.getaddr),
    free_temp_buffers = interp2app(W_FuncPtr.free_temp_buffers),
    fromaddr = interp2app(descr_fromaddr, as_classmethod=True)
    )



# ========================================================================

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        self.space = space
        if name is None:
            self.name = "<None>"
        else:
            self.name = name
        try:
            self.cdll = libffi.CDLL(name)
        except DLOpenError, e:
            raise operationerrfmt(space.w_OSError, '%s: %s', self.name,
                                  e.msg or 'unspecified error')

    @unwrap_spec(name=str)
    def getfunc(self, space, name, w_argtypes, w_restype):
        argtypes_w, argtypes, w_restype, restype = unpack_argtypes(space,
                                                                   w_argtypes,
                                                                   w_restype)
        try:
            func = self.cdll.getpointer(name, argtypes, restype)
        except KeyError:
            raise operationerrfmt(space.w_AttributeError,
                                  "No symbol %s found in library %s", name, self.name)

        return W_FuncPtr(func, argtypes_w, w_restype)

    @unwrap_spec(name=str)
    def getaddressindll(self, space, name):
        try:
            address_as_uint = rffi.cast(lltype.Unsigned,
                                        self.cdll.getaddressindll(name))
        except KeyError:
            raise operationerrfmt(space.w_ValueError,
                                  "No symbol %s found in library %s", name, self.name)
        return space.wrap(address_as_uint)

@unwrap_spec(name='str_or_None')
def descr_new_cdll(space, w_type, name):
    return space.wrap(W_CDLL(space, name))


W_CDLL.typedef = TypeDef(
    '_ffi.CDLL',
    __new__     = interp2app(descr_new_cdll),
    getfunc     = interp2app(W_CDLL.getfunc),
    getaddressindll = interp2app(W_CDLL.getaddressindll),
    )

# ========================================================================

def get_libc(space):
    from pypy.rlib.clibffi import get_libc_name
    try:
        return space.wrap(W_CDLL(space, get_libc_name()))
    except OSError, e:
        raise wrap_oserror(space, e)

