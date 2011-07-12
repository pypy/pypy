import sys
from pypy.interpreter.baseobjspace import Wrappable, Arguments
from pypy.interpreter.error import OperationError, wrap_oserror, \
    operationerrfmt
from pypy.interpreter.gateway import interp2app, NoneNotWrapped, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module._rawffi.structure import W_StructureInstance, W_Structure
#
from pypy.rpython.lltypesystem import lltype, rffi
#
from pypy.rlib import jit
from pypy.rlib import libffi
from pypy.rlib.rdynload import DLOpenError
from pypy.rlib.rarithmetic import intmask, r_uint

class W_FFIType(Wrappable):

    _immutable_fields_ = ['name', 'ffitype', 'w_datashape', 'w_pointer_to']
    
    def __init__(self, name, ffitype, w_datashape=None, w_pointer_to=None):
        self.name = name
        self.ffitype = ffitype
        self.w_datashape = w_datashape
        self.w_pointer_to = w_pointer_to
        if self.is_struct():
            assert w_datashape is not None

    def descr_deref_pointer(self, space):
        if self.w_pointer_to is None:
            return space.w_None
        return self.w_pointer_to

    def repr(self, space):
        return space.wrap(self.__repr__())

    def __repr__(self):
        return "<ffi type %s>" % self.name

    def is_signed(self):
        return (self is app_types.slong or
                self is app_types.sint or
                self is app_types.sshort or
                self is app_types.sbyte or
                self is app_types.slonglong)

    def is_unsigned(self):
        return (self is app_types.ulong or
                self is app_types.uint or
                self is app_types.ushort or
                self is app_types.ubyte or
                self is app_types.ulonglong)

    def is_pointer(self):
        return self.ffitype is libffi.types.pointer

    def is_char(self):
        return self is app_types.char

    def is_unichar(self):
        return self is app_types.unichar

    def is_longlong(self):
        return libffi.IS_32_BIT and (self is app_types.slonglong or
                                     self is app_types.ulonglong)

    def is_double(self):
        return self is app_types.double

    def is_singlefloat(self):
        return self is app_types.float

    def is_void(self):
        return self is app_types.void

    def is_struct(self):
        return libffi.types.is_struct(self.ffitype)

W_FFIType.typedef = TypeDef(
    'FFIType',
    __repr__ = interp2app(W_FFIType.repr),
    deref_pointer = interp2app(W_FFIType.descr_deref_pointer),
    )


def build_ffi_types():
    from pypy.rlib.clibffi import FFI_TYPE_P
    types = [
        # note: most of the type name directly come from the C equivalent,
        # with the exception of bytes: in C, ubyte and char are equivalent,
        # but for _ffi the first expects a number while the second a 1-length
        # string
        W_FFIType('slong',     libffi.types.slong),
        W_FFIType('sint',      libffi.types.sint),
        W_FFIType('sshort',    libffi.types.sshort),
        W_FFIType('sbyte',     libffi.types.schar),
        W_FFIType('slonglong', libffi.types.slonglong),
        #
        W_FFIType('ulong',     libffi.types.ulong),
        W_FFIType('uint',      libffi.types.uint),
        W_FFIType('ushort',    libffi.types.ushort),
        W_FFIType('ubyte',     libffi.types.uchar),
        W_FFIType('ulonglong', libffi.types.ulonglong),
        #
        W_FFIType('char',      libffi.types.uchar),
        W_FFIType('unichar',   libffi.types.wchar_t),
        #
        W_FFIType('double',    libffi.types.double),
        W_FFIType('float',     libffi.types.float),
        W_FFIType('void',      libffi.types.void),
        W_FFIType('void_p',    libffi.types.pointer),
        #
        # missing types:

        ## 's' : ffi_type_pointer,
        ## 'z' : ffi_type_pointer,
        ## 'O' : ffi_type_pointer,
        ## 'Z' : ffi_type_pointer,

        ]
    return dict([(t.name, t) for t in types])

class app_types:
    pass
app_types.__dict__ = build_ffi_types()

def descr_new_pointer(space, w_cls, w_pointer_to):
    try:
        return descr_new_pointer.cache[w_pointer_to]
    except KeyError:
        w_pointer_to = space.interp_w(W_FFIType, w_pointer_to)
        name = '(pointer to %s)' % w_pointer_to.name
        w_result = W_FFIType(name, libffi.types.pointer, w_pointer_to = w_pointer_to)
        descr_new_pointer.cache[w_pointer_to] = w_result
        return w_result
descr_new_pointer.cache = {}

class W_types(Wrappable):
    pass
W_types.typedef = TypeDef(
    'types',
    Pointer = interp2app(descr_new_pointer, as_classmethod=True),
    **app_types.__dict__)


def unwrap_ffitype(space, w_argtype, allow_void=False):
    res = w_argtype.ffitype
    if res is libffi.types.void and not allow_void:
        msg = 'void is not a valid argument type'
        raise OperationError(space.w_TypeError, space.wrap(msg))
    return res

def unwrap_truncate_int(TP, space, w_arg):
    if space.is_true(space.isinstance(w_arg, space.w_int)):
        return rffi.cast(TP, space.int_w(w_arg))
    else:
        return rffi.cast(TP, space.bigint_w(w_arg).ulonglongmask())
unwrap_truncate_int._annspecialcase_ = 'specialize:arg(0)'

# ========================================================================

class W_FuncPtr(Wrappable):

    _immutable_fields_ = ['func', 'argtypes_w[*]', 'w_restype']
    
    def __init__(self, func, argtypes_w, w_restype):
        self.func = func
        self.argtypes_w = argtypes_w
        self.w_restype = w_restype

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
        for i in range(expected):
            w_argtype = self.argtypes_w[i]
            w_arg = args_w[i]
            if w_argtype.is_longlong():
                # note that we must check for longlong first, because either
                # is_signed or is_unsigned returns true anyway
                assert libffi.IS_32_BIT
                kind = libffi.types.getkind(w_argtype.ffitype) # XXX: remove the kind
                self.arg_longlong(space, argchain, kind, w_arg)
            elif w_argtype.is_signed():
                argchain.arg(unwrap_truncate_int(rffi.LONG, space, w_arg))
            elif w_argtype.is_pointer():
                w_arg = self.convert_pointer_arg_maybe(space, w_arg, w_argtype)
                argchain.arg(intmask(space.uint_w(w_arg)))
            elif w_argtype.is_unsigned():
                argchain.arg(unwrap_truncate_int(rffi.ULONG, space, w_arg))
            elif w_argtype.is_char():
                w_arg = space.ord(w_arg)
                argchain.arg(space.int_w(w_arg))
            elif w_argtype.is_unichar():
                w_arg = space.ord(w_arg)
                argchain.arg(space.int_w(w_arg))
            elif w_argtype.is_double():
                argchain.arg(space.float_w(w_arg))
            elif w_argtype.is_singlefloat():
                argchain.arg_singlefloat(space.float_w(w_arg))
            elif w_argtype.is_struct():
                # arg_raw directly takes value to put inside ll_args
                w_arg = space.interp_w(W_StructureInstance, w_arg)                
                ptrval = w_arg.ll_buffer
                argchain.arg_raw(ptrval)
            else:
                assert False, "Argument shape '%s' not supported" % w_argtype
        return argchain

    def convert_pointer_arg_maybe(self, space, w_arg, w_argtype):
        """
        Try to convert the argument by calling _as_ffi_pointer_()
        """
        meth = space.lookup(w_arg, '_as_ffi_pointer_') # this also promotes the type
        if meth:
            return space.call_function(meth, w_arg, w_argtype)
        else:
            return w_arg

    @jit.dont_look_inside
    def arg_longlong(self, space, argchain, kind, w_arg):
        bigarg = space.bigint_w(w_arg)
        if kind == 'I':
            llval = bigarg.tolonglong()
        elif kind == 'U':
            ullval = bigarg.toulonglong()
            llval = rffi.cast(rffi.LONGLONG, ullval)
        else:
            assert False
        # this is a hack: we store the 64 bits of the long long into the
        # 64 bits of a float (i.e., a C double)
        floatval = libffi.longlong2float(llval)
        argchain.arg_longlong(floatval)

    def call(self, space, args_w):
        self = jit.promote(self)
        argchain = self.build_argchain(space, args_w)
        w_restype = self.w_restype
        if w_restype.is_longlong():
            # note that we must check for longlong first, because either
            # is_signed or is_unsigned returns true anyway
            assert libffi.IS_32_BIT
            reskind = libffi.types.getkind(self.func.restype) # XXX: remove the kind
            return self._call_longlong(space, argchain, reskind)
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
            floatres = self.func.call(argchain, rffi.DOUBLE)
            return space.wrap(floatres)
        elif w_restype.is_singlefloat():
            # the result is a float, but widened to be inside a double
            floatres = self.func.call(argchain, rffi.FLOAT)
            return space.wrap(floatres)
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

    @jit.dont_look_inside
    def _call_longlong(self, space, argchain, reskind):
        # this is a hack: we store the 64 bits of the long long into the 64
        # bits of a float (i.e., a C double)
        floatres = self.func.call(argchain, rffi.LONGLONG)
        llres = libffi.float2longlong(floatres)
        if reskind == 'I':
            return space.wrap(llres)
        elif reskind == 'U':
            ullres = rffi.cast(rffi.ULONGLONG, llres)
            return space.wrap(ullres)
        else:
            assert False

    def getaddr(self, space):
        """
        Return the physical address in memory of the function
        """
        return space.wrap(rffi.cast(rffi.LONG, self.func.funcsym))



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
