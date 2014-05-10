from rpython.rlib import rmpdec, rarithmetic, rbigint, rfloat
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rstring import StringBuilder
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt, OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.typedef import (TypeDef, GetSetProperty, descr_get_dict,
    descr_set_dict, descr_del_dict)
from pypy.objspace.std import unicodeobject
from pypy.module._decimal import interp_context


IEEE_CONTEXT_MAX_BITS = rmpdec.MPD_IEEE_CONTEXT_MAX_BITS
MAX_PREC = rmpdec.MPD_MAX_PREC
# DEC_MINALLOC >= MPD_MINALLOC
DEC_MINALLOC = 4

class W_Decimal(W_Root):
    hash = -1

    def __init__(self, space):
        self.mpd = lltype.malloc(rmpdec.MPD_PTR.TO, flavor='raw')
        self.data = lltype.malloc(rmpdec.MPD_UINT_PTR.TO,
                                  DEC_MINALLOC, flavor='raw')
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

    @staticmethod
    def allocate(space, w_subtype=None):
        if w_subtype:
            w_result = space.allocate_instance(W_Decimal, w_subtype)
            W_Decimal.__init__(w_result, space)
        else:
            w_result = W_Decimal(space)
        return w_result

    def apply(self, space, context, w_subtype=None):
        # Apply the context to the input operand. Return a new W_Decimal.
        w_result = W_Decimal.allocate(space, w_subtype)
        with context.catch_status(space) as (ctx, status_ptr):
            rmpdec.mpd_qcopy(w_result.mpd, self.mpd, status_ptr)
            rmpdec.mpd_qfinalize(w_result.mpd, context.ctx, status_ptr)
        return w_result

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

    def descr_repr(self, space):
        context = interp_context.getcontext(space)
        cp = rmpdec.mpd_to_sci(self.mpd, context.capitals)
        if not cp:
            raise OperationError(space.w_MemoryError, space.w_None)
        try:
            result = rffi.charp2str(cp)
        finally:
            rmpdec.mpd_free(cp)
        return space.wrap("Decimal('%s')" % result)

    def descr_bool(self, space):
        return space.wrap(not rmpdec.mpd_iszero(self.mpd))

    def descr_float(self, space):
        if rmpdec.mpd_isnan(self.mpd):
            if rmpdec.mpd_issnan(self.mpd):
                raise oefmt(space.w_ValueError,
                            "cannot convert signaling NaN to float")
            if rmpdec.mpd_isnegative(self.mpd):
                w_s = space.wrap("-nan")
            else:
                w_s = space.wrap("nan")
        else:
            w_s = self.descr_str(space)
        return space.call_function(space.w_float, w_s)

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

    # Operations
    @staticmethod
    def convert_op(space, w_value, context):
        if isinstance(w_value, W_Decimal):
            return None, w_value
        elif space.isinstance_w(w_value, space.w_int):
            value = space.bigint_w(w_value)
            return None, decimal_from_bigint(space, None, value, context,
                                             exact=True)
        return space.w_NotImplemented, None

    def convert_binop(self, space, w_other, context):
        w_err, w_a = W_Decimal.convert_op(space, self, context)
        if w_err:
            return w_err, None, None
        w_err, w_b = W_Decimal.convert_op(space, w_other, context)
        if w_err:
            return w_err, None, None
        return None, w_a, w_b

    def binary_number_method(self, space, mpd_func, w_other):
        context = interp_context.getcontext(space)

        w_err, w_a, w_b = self.convert_binop(space, w_other, context)
        if w_err:
            return w_err
        w_result = W_Decimal.allocate(space)
        with context.catch_status(space) as (ctx, status_ptr):
            mpd_func(w_result.mpd, w_a.mpd, w_b.mpd, ctx, status_ptr)
        return w_result

    def descr_add(self, space, w_other):
        return self.binary_number_method(space, rmpdec.mpd_qadd, w_other)
    def descr_sub(self, space, w_other):
        return self.binary_number_method(space, rmpdec.mpd_qsub, w_other)
    def descr_mul(self, space, w_other):
        return self.binary_number_method(space, rmpdec.mpd_qmul, w_other)
    def descr_truediv(self, space, w_other):
        return self.binary_number_method(space, rmpdec.mpd_qdiv, w_other)

    # Boolean functions
    def is_qnan_w(self, space):
        return space.wrap(bool(rmpdec.mpd_isqnan(self.mpd)))
    def is_infinite_w(self, space):
        return space.wrap(bool(rmpdec.mpd_isinfinite(self.mpd)))


# Constructors
def decimal_from_ssize(space, w_subtype, value, context, exact=True):
    w_result = W_Decimal.allocate(space, w_subtype)
    with interp_context.ConvContext(
            space, w_result.mpd, context, exact) as (ctx, status_ptr):
        rmpdec.mpd_qset_ssize(w_result.mpd, value, ctx, status_ptr)
    return w_result

def decimal_from_cstring(space, w_subtype, value, context, exact=True):
    w_result = W_Decimal.allocate(space, w_subtype)
    with interp_context.ConvContext(
            space, w_result.mpd, context, exact) as (ctx, status_ptr):
        rmpdec.mpd_qset_string(w_result.mpd, value, ctx, status_ptr)
    return w_result

def decimal_from_unicode(space, w_subtype, w_value, context, exact=True,
                         strip_whitespace=True):
    s = unicodeobject.unicode_to_decimal_w(space, w_value)
    if '\0' in s:
        s = ''  # empty string triggers ConversionSyntax.
    if strip_whitespace:
        s = s.strip()
    return decimal_from_cstring(space, w_subtype, s, context, exact=exact)

def decimal_from_bigint(space, w_subtype, value, context, exact=True):
    w_result = W_Decimal.allocate(space, w_subtype)

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

def decimal_from_tuple(space, w_subtype, w_value, context, exact=True):
    w_sign, w_digits, w_exponent  = space.unpackiterable(w_value, 3)

    # Make a string representation of a DecimalTuple
    builder = StringBuilder(20)

    # sign
    try:
        sign = space.int_w(w_sign)
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
        sign = -1
    if sign != 0 and sign != 1:
        raise oefmt(space.w_ValueError,
                    "sign must be an integer with the value 0 or 1")
    builder.append('-' if sign else '+')

    # exponent or encoding for a special number
    is_infinite = False
    is_special = False
    exponent = 0
    if space.isinstance_w(w_exponent, space.w_unicode):
        # special
        is_special = True
        val = space.unicode_w(w_exponent)
        if val == u'F':
            builder.append('Inf')
            is_infinite = True
        elif val == u'n':
            builder.append('Nan')
        elif val == u'N':
            builder.append('sNan')
        else:
            raise oefmt(space.w_ValueError,
                        "string argument in the third position "
                        "must be 'F', 'n' or 'N'")
    else:
        # exponent
        try:
            exponent = space.int_w(w_exponent)
        except OperationError as e:
            if not e.match(space, space.w_TypeError):
                raise
            raise oefmt(space.w_ValueError,
                        "exponent must be an integer")            

    # coefficient
    digits_w = space.unpackiterable(w_digits)

    if not digits_w and not is_special:
        # empty tuple: zero coefficient, except for special numbers
        builder.append('0')
    for w_digit in digits_w:
        try:
            digit = space.int_w(w_digit)
        except OperationError as e:
            if not e.match(space, space.w_TypeError):
                raise
            digit = -1
        if not 0 <= digit <= 9:
            raise oefmt(space.w_ValueError,
                        "coefficient must be a tuple of digits")
        if is_infinite:
            # accept but ignore any well-formed coefficient for
            # compatibility with decimal.py
            continue
        builder.append(chr(ord('0') + digit))
            
    if not is_special:
        builder.append('E')
        builder.append(str(exponent))

    strval = builder.build()
    return decimal_from_cstring(space, w_subtype, strval, context, exact=exact)

def decimal_from_decimal(space, w_subtype, w_value, context, exact=True):
    assert isinstance(w_value, W_Decimal)
    if exact:
        if space.is_w(w_subtype, space.gettypeobject(W_Decimal.typedef)):
            return w_value
        w_result = W_Decimal.allocate(space, w_subtype)
        with interp_context.ConvContext(
                space, w_result.mpd, context, exact) as (ctx, status_ptr):
            rmpdec.mpd_qcopy(w_result.mpd, w_value.mpd, status_ptr)
        return w_result
    else:
        if (rmpdec.mpd_isnan(w_value.mpd) and
            w_value.mpd.c_digits > (
                context.ctx.c_prec - rffi.cast(lltype.Signed,
                                               context.ctx.c_clamp))):
            # Special case: too many NaN payload digits
            context.addstatus(space, rmpdec.MPD_Conversion_syntax)
            w_result = W_Decimal.allocate(space, w_subtype)
            rmpdec.mpd_setspecial(w_result.mpd, rmpdec.MPD_POS, rmpdec.MPD_NAN)
            return w_result
        else:
            return w_value.apply(space, context)

def decimal_from_float(space, w_subtype, w_value, context, exact=True):
    value = space.float_w(w_value)
    sign = 0 if rfloat.copysign(1.0, value) == 1.0 else 1

    if rfloat.isnan(value):
        w_result = W_Decimal.allocate(space, w_subtype)
        # decimal.py calls repr(float(+-nan)), which always gives a
        # positive result.
        rmpdec.mpd_setspecial(w_result.mpd, rmpdec.MPD_POS, rmpdec.MPD_NAN)
        return w_result
    if rfloat.isinf(value):
        w_result = W_Decimal.allocate(space, w_subtype)
        rmpdec.mpd_setspecial(w_result.mpd, sign, rmpdec.MPD_INF)
        return w_result

    # float as integer ratio: numerator/denominator
    num, den = rfloat.float_as_rbigint_ratio(abs(value))
    k = den.bit_length() - 1

    w_result = decimal_from_bigint(space, w_subtype, num, context, exact=True)

    # Compute num * 5**k
    d1 = rmpdec.mpd_qnew()
    if not d1:
        raise OperationError(space.w_MemoryError, space.w_None)
    d2 = rmpdec.mpd_qnew()
    if not d2:
        raise OperationError(space.w_MemoryError, space.w_None)
    with interp_context.ConvContext(
            space, w_result.mpd, context, exact=True) as (ctx, status_ptr):
        rmpdec.mpd_qset_uint(d1, 5, ctx, status_ptr)
        rmpdec.mpd_qset_ssize(d2, k, ctx, status_ptr)
        rmpdec.mpd_qpow(d1, d1, d2, ctx, status_ptr)
    with interp_context.ConvContext(
            space, w_result.mpd, context, exact=True) as (ctx, status_ptr):
        rmpdec.mpd_qmul(w_result.mpd, w_result.mpd, d1, ctx, status_ptr)

    # result = +- n * 5**k * 10**-k
    rmpdec.mpd_set_sign(w_result.mpd, sign)
    w_result.mpd.c_exp = - k

    if not exact:
        with context.catch_status(space) as (ctx, status_ptr):
            rmpdec.mpd_qfinalize(w_result.mpd, ctx, status_ptr)
    return w_result

def decimal_from_object(space, w_subtype, w_value, context, exact=True):
    if w_value is None:
        return decimal_from_ssize(space, w_subtype, 0, context, exact=exact)
    elif isinstance(w_value, W_Decimal):
        return decimal_from_decimal(space, w_subtype, w_value, context,
                                    exact=exact)
    elif space.isinstance_w(w_value, space.w_unicode):
        return decimal_from_unicode(space, w_subtype, w_value, context,
                                    exact=exact, strip_whitespace=exact)
    elif space.isinstance_w(w_value, space.w_int):
        value = space.bigint_w(w_value)
        return decimal_from_bigint(space, w_subtype, value, context,
                                   exact=exact)
    elif (space.isinstance_w(w_value, space.w_list) or
          space.isinstance_w(w_value, space.w_tuple)):
        return decimal_from_tuple(space, w_subtype, w_value, context,
                                 exact=exact)
    elif space.isinstance_w(w_value, space.w_float):
        context.addstatus(space, rmpdec.MPD_Float_operation)
        return decimal_from_float(space, w_subtype, w_value, context,
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
    __repr__ = interp2app(W_Decimal.descr_repr),
    __bool__ = interp2app(W_Decimal.descr_bool),
    __float__ = interp2app(W_Decimal.descr_float),
    __eq__ = interp2app(W_Decimal.descr_eq),
    #
    __add__ = interp2app(W_Decimal.descr_add),
    __sub__ = interp2app(W_Decimal.descr_sub),
    __mul__ = interp2app(W_Decimal.descr_mul),
    __truediv__ = interp2app(W_Decimal.descr_truediv),
    #
    is_qnan = interp2app(W_Decimal.is_qnan_w),
    is_infinite = interp2app(W_Decimal.is_infinite_w),
    )
