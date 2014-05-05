from rpython.rlib import rmpdec, rarithmetic, rbigint
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt, OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.typedef import (TypeDef, GetSetProperty, descr_get_dict,
    descr_set_dict, descr_del_dict)
from pypy.module._decimal import interp_context


IEEE_CONTEXT_MAX_BITS = rmpdec.MPD_IEEE_CONTEXT_MAX_BITS
MAX_PREC = rmpdec.MPD_MAX_PREC
# DEC_MINALLOC >= MPD_MINALLOC
DEC_MINALLOC = 4

class W_Decimal(W_Root):
    hash = -1

    def __init__(self, space):
        self.mpd = lltype.malloc(rmpdec.MPD_PTR.TO, flavor='raw')
        self.data = lltype.malloc(rffi.UINTP.TO, DEC_MINALLOC, flavor='raw')
        rffi.setintfield(self.mpd, 'c_flags',
                         rmpdec.MPD_STATIC | rmpdec.MPD_STATIC_DATA)
        self.mpd.c_exp = 0
        self.mpd.c_digits = 0
        self.mpd.c_len = 0
        self.mpd.c_alloc = DEC_MINALLOC
        self.mpd.c_data = self.data

    def __del__(self):
        if self.mpd:
            lltype.free(self.mpd, flavor='raw')
        if self.data:
            lltype.free(self.data, flavor='raw')

    def descr_str(self, space):
        context = interp_context.getcontext(space)
        with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as cp_ptr:
            size = rmpdec.mpd_to_sci_size(cp_ptr, self.mpd, context.capitals)
            if size < 0:
                raise OperationError(space.w_MemoryError, space.w_None)
            cp = cp_ptr[0]
            try:
                result = rffi.charpsize2str(cp, size)
            finally:
                rmpdec.mpd_free(cp)
        return space.wrap(result)  # Convert bytes to unicode

    def compare(self, space, w_other, op):
        if not isinstance(w_other, W_Decimal):  # So far
            return space.w_NotImplemented
        with lltype.scoped_alloc(rffi.CArrayPtr(rffi.UINT).TO, 1) as status_ptr:
            r = rmpdec.mpd_qcmp(self.mpd, w_other.mpd, status_ptr)
        if op == 'eq':
            return space.wrap(r == 0)
        else:
            return space.w_NotImplemented

    def descr_eq(self, space, w_other):
        return self.compare(space, w_other, 'eq')


# Constructors
def decimal_from_ssize(space, w_subtype, value, context, exact=True):
    w_result = space.allocate_instance(W_Decimal, w_subtype)
    W_Decimal.__init__(w_result, space)
    with interp_context.ConvContext(
            space, w_result.mpd, context, exact) as (ctx, status_ptr):
        rmpdec.mpd_qset_ssize(w_result.mpd, value, ctx, status_ptr)
    return w_result

def decimal_from_cstring(space, w_subtype, value, context, exact=True):
    w_result = space.allocate_instance(W_Decimal, w_subtype)
    W_Decimal.__init__(w_result, space)

    with interp_context.ConvContext(
            space, w_result.mpd, context, exact) as (ctx, status_ptr):
        rmpdec.mpd_qset_string(w_result.mpd, value, ctx, status_ptr)
    return w_result

def decimal_from_unicode(space, w_subtype, w_value, context, exact=True,
                         strip_whitespace=True):
    s = space.str_w(w_value)  # XXX numeric_as_ascii() is different
    if strip_whitespace:
        s = s.strip()
    return decimal_from_cstring(space, w_subtype, s, context, exact=exact)

def decimal_from_long(space, w_subtype, w_value, context, exact=True):
    w_result = space.allocate_instance(W_Decimal, w_subtype)
    W_Decimal.__init__(w_result, space)

    value = space.bigint_w(w_value)

    with interp_context.ConvContext(
            space, w_result.mpd, context, exact) as (ctx, status_ptr):
        if value.sign == -1:
            size = value.numdigits()
            sign = rmpdec.MPD_NEG
        else:
            size = value.numdigits()
            sign = rmpdec.MPD_POS
        if rbigint.UDIGIT_TYPE.BITS == 32:
            with lltype.scoped_alloc(rffi.CArrayPtr(rffi.UINT).TO, size) as digits:
                for i in range(size):
                    digits[i] = value.udigit(i)
                rmpdec.mpd_qimport_u32(
                    w_result.mpd, digits, size, sign, PyLong_BASE,
                    ctx, status_ptr)
        elif rbigint.UDIGIT_TYPE.BITS == 64:
            # No mpd_qimport_u64, so we convert to a string.
            return decimal_from_cstring(space, w_subtype, value.str(),
                                        context, exact=exact)
                                       
        else:
            raise ValueError("Bad rbigint size")
    return w_result

def decimal_from_object(space, w_subtype, w_value, context, exact=True):
    if w_value is None:
        return decimal_from_ssize(space, w_subtype, 0, context, exact=exact)
    elif space.isinstance_w(w_value, space.w_unicode):
        return decimal_from_unicode(space, w_subtype, w_value, context,
                                    exact=exact, strip_whitespace=exact)
    elif space.isinstance_w(w_value, space.w_int):
        return decimal_from_long(space, w_subtype, w_value, context,
                                 exact=exact)
    raise oefmt(space.w_TypeError,
                "conversion from %N to Decimal is not supported",
                space.type(w_value))

@unwrap_spec(w_context=WrappedDefault(None))
def descr_new_decimal(space, w_subtype, w_value=None, w_context=None):
    context = interp_context.ensure_context(space, w_context)
    return decimal_from_object(space, w_subtype, w_value, context,
                               exact=True)

W_Decimal.typedef = TypeDef(
    'Decimal',
    __new__ = interp2app(descr_new_decimal),
    __str__ = interp2app(W_Decimal.descr_str),
    __eq__ = interp2app(W_Decimal.descr_eq),
    )
