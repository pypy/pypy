from pypy.rlib import libffi
from pypy.rlib import jit
from pypy.rlib.rarithmetic import intmask, r_uint
from pypy.rpython.lltypesystem import rffi
from pypy.module._rawffi.structure import W_StructureInstance, W_Structure
from pypy.module._ffi.interp_ffitype import app_types

class UnwrapDispatcher(object):

    def __init__(self, space):
        self.space = space

    def unwrap_and_do(self, w_ffitype, w_obj):
        space = self.space
        if w_ffitype.is_longlong():
            # note that we must check for longlong first, because either
            # is_signed or is_unsigned returns true anyway
            assert libffi.IS_32_BIT
            self._longlong(w_ffitype, w_obj)
        elif w_ffitype.is_signed():
            intval = space.truncatedint_w(w_obj)
            self.handle_signed(w_ffitype, w_obj, intval)
        elif self.maybe_handle_char_or_unichar_p(w_ffitype, w_obj):
            # the object was already handled from within
            # maybe_handle_char_or_unichar_p
            pass
        elif w_ffitype.is_pointer():
            w_obj = self.convert_pointer_arg_maybe(w_obj, w_ffitype)
            intval = intmask(space.uint_w(w_obj))
            self.handle_pointer(w_ffitype, w_obj, intval)
        elif w_ffitype.is_unsigned():
            uintval = r_uint(space.truncatedint_w(w_obj))
            self.handle_unsigned(w_ffitype, w_obj, uintval)
        elif w_ffitype.is_char():
            intval = space.int_w(space.ord(w_obj))
            self.handle_char(w_ffitype, w_obj, intval)
        elif w_ffitype.is_unichar():
            intval = space.int_w(space.ord(w_obj))
            self.handle_unichar(w_ffitype, w_obj, intval)
        elif w_ffitype.is_double():
            self._float(w_ffitype, w_obj)
        elif w_ffitype.is_singlefloat():
            self._singlefloat(w_ffitype, w_obj)
        elif w_ffitype.is_struct():
            # arg_raw directly takes value to put inside ll_args
            w_obj = space.interp_w(W_StructureInstance, w_obj)
            self.handle_struct(w_ffitype, w_obj)
        else:
            self.error(w_ffitype, w_obj)

    def _longlong(self, w_ffitype, w_obj):
        # a separate function, which can be seen by the jit or not,
        # depending on whether longlongs are supported
        bigval = self.space.bigint_w(w_obj)
        ullval = bigval.ulonglongmask()
        llval = rffi.cast(rffi.LONGLONG, ullval)
        self.handle_longlong(w_ffitype, w_obj, llval)

    def _float(self, w_ffitype, w_obj):
        # a separate function, which can be seen by the jit or not,
        # depending on whether floats are supported
        floatval = self.space.float_w(w_obj)
        self.handle_float(w_ffitype, w_obj, floatval)

    def _singlefloat(self, w_ffitype, w_obj):
        # a separate function, which can be seen by the jit or not,
        # depending on whether singlefloats are supported
        from pypy.rlib.rarithmetic import r_singlefloat
        floatval = self.space.float_w(w_obj)
        singlefloatval = r_singlefloat(floatval)
        self.handle_singlefloat(w_ffitype, w_obj, singlefloatval)

    def maybe_handle_char_or_unichar_p(self, w_ffitype, w_obj):
        w_type = jit.promote(self.space.type(w_obj))
        if w_ffitype.is_char_p() and w_type is self.space.w_str:
            strval = self.space.str_w(w_obj)
            self.handle_char_p(w_ffitype, w_obj, strval)
            return True
        elif w_ffitype.is_unichar_p() and (w_type is self.space.w_str or
                                           w_type is self.space.w_unicode):
            unicodeval = self.space.unicode_w(w_obj)
            self.handle_unichar_p(w_ffitype, w_obj, unicodeval)
            return True

    def convert_pointer_arg_maybe(self, w_arg, w_argtype):
        """
        Try to convert the argument by calling _as_ffi_pointer_()
        """
        space = self.space
        meth = space.lookup(w_arg, '_as_ffi_pointer_') # this also promotes the type
        if meth:
            return space.call_function(meth, w_arg, w_argtype)
        else:
            return w_arg

    def error(self, w_ffitype, w_obj):
        assert False # XXX raise a proper app-level exception

    def handle_signed(self, w_ffitype, w_obj, intval):
        """
        intval: lltype.Signed
        """
        self.error(w_ffitype, w_obj)

    def handle_unsigned(self, w_ffitype, w_obj, uintval):
        """
        uintval: lltype.Unsigned
        """
        self.error(w_ffitype, w_obj)

    def handle_pointer(self, w_ffitype, w_obj, intval):
        """
        intval: lltype.Signed
        """
        self.error(w_ffitype, w_obj)

    def handle_char(self, w_ffitype, w_obj, intval):
        """
        intval: lltype.Signed
        """
        self.error(w_ffitype, w_obj)
        
    def handle_unichar(self, w_ffitype, w_obj, intval):
        """
        intval: lltype.Signed
        """
        self.error(w_ffitype, w_obj)

    def handle_longlong(self, w_ffitype, w_obj, longlongval):
        """
        longlongval: lltype.SignedLongLong
        """
        self.error(w_ffitype, w_obj)

    def handle_char_p(self, w_ffitype, w_obj, strval):
        """
        strval: interp-level str
        """
        self.error(w_ffitype, w_obj)

    def handle_unichar_p(self, w_ffitype, w_obj, unicodeval):
        """
        unicodeval: interp-level unicode
        """
        self.error(w_ffitype, w_obj)

    def handle_float(self, w_ffitype, w_obj, floatval):
        """
        floatval: lltype.Float
        """
        self.error(w_ffitype, w_obj)

    def handle_singlefloat(self, w_ffitype, w_obj, singlefloatval):
        """
        singlefloatval: lltype.SingleFloat
        """
        self.error(w_ffitype, w_obj)

    def handle_struct(self, w_ffitype, w_structinstance):
        """
        w_structinstance: W_StructureInstance
        """
        self.error(w_ffitype, w_structinstance)



class WrapDispatcher(object):

    def __init__(self, space):
        self.space = space

    def do_and_wrap(self, w_ffitype):
        space = self.space
        if w_ffitype.is_longlong():
            # note that we must check for longlong first, because either
            # is_signed or is_unsigned returns true anyway
            assert libffi.IS_32_BIT
            return self._longlong(w_ffitype)
        elif w_ffitype.is_signed():
            intval = self.get_signed(w_ffitype)
            return space.wrap(intval)
        elif w_ffitype is app_types.ulong:
            # we need to be careful when the return type is ULONG, because the
            # value might not fit into a signed LONG, and thus might require
            # and app-evel <long>.  This is why we need to treat it separately
            # than the other unsigned types.
            uintval = self.get_unsigned(w_ffitype)
            return space.wrap(uintval)
        elif w_ffitype.is_unsigned(): # note that ulong is handled just before
            intval = self.get_unsigned_which_fits_into_a_signed(w_ffitype)
            return space.wrap(intval)
        elif w_ffitype.is_pointer():
            uintval = self.get_pointer(w_ffitype)
            return space.wrap(uintval)
        elif w_ffitype.is_char():
            ucharval = self.get_char(w_ffitype)
            return space.wrap(chr(ucharval))
        elif w_ffitype.is_unichar():
            wcharval = self.get_unichar(w_ffitype)
            return space.wrap(unichr(wcharval))
        elif w_ffitype.is_double():
            return self._float(w_ffitype)
        elif w_ffitype.is_singlefloat():
            return self._singlefloat(w_ffitype)
        elif w_ffitype.is_struct():
            w_datashape = w_ffitype.w_datashape
            assert isinstance(w_datashape, W_Structure)
            uintval = self.get_struct(w_datashape) # this is the ptr to the struct
            return w_datashape.fromaddress(space, uintval)
        elif w_ffitype.is_void():
            voidval = self.get_void(w_ffitype)
            assert voidval is None
            return space.w_None
        else:
            assert False, "Return value shape '%s' not supported" % w_ffitype

    def _longlong(self, w_ffitype):
        # a separate function, which can be seen by the jit or not,
        # depending on whether longlongs are supported
        if w_ffitype is app_types.slonglong:
            longlongval = self.get_longlong(w_ffitype)
            return self.space.wrap(longlongval)
        elif w_ffitype is app_types.ulonglong:
            ulonglongval = self.get_ulonglong(w_ffitype)
            return self.space.wrap(ulonglongval)
        else:
            self.error(w_ffitype)

    def _float(self, w_ffitype):
        # a separate function, which can be seen by the jit or not,
        # depending on whether floats are supported
        floatval = self.get_float(w_ffitype)
        return self.space.wrap(floatval)

    def _singlefloat(self, w_ffitype):
        # a separate function, which can be seen by the jit or not,
        # depending on whether singlefloats are supported
        singlefloatval = self.get_singlefloat(w_ffitype)
        return self.space.wrap(float(singlefloatval))

    def error(self, w_ffitype, w_obj):
        assert False # XXX raise a proper app-level exception

    def get_longlong(self, w_ffitype):
        self.error(w_ffitype)

    def get_ulonglong(self, w_ffitype):
        self.error(w_ffitype)

    def get_signed(self, w_ffitype):
        self.error(w_ffitype)

    def get_unsigned(self, w_ffitype):
        self.error(w_ffitype)

    def get_unsigned_which_fits_into_a_signed(self, w_ffitype):
        self.error(w_ffitype)

    def get_pointer(self, w_ffitype):
        self.error(w_ffitype)

    def get_char(self, w_ffitype):
        self.error(w_ffitype)

    def get_unichar(self, w_ffitype):
        self.error(w_ffitype)

    def get_float(self, w_ffitype):
        self.error(w_ffitype)

    def get_singlefloat(self, w_ffitype):
        self.error(w_ffitype)

    def get_struct(self, w_datashape):
        """
        XXX: write nice docstring in the base class, must return an ULONG
        """
        return self.func.call(self.argchain, rffi.ULONG, is_struct=True)

    def get_void(self, w_ffitype):
        self.error(w_ffitype)
