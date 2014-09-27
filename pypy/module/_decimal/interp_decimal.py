from rpython.rlib import rmpdec, rarithmetic, rbigint, rfloat
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rstring import StringBuilder
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.tool.sourcetools import func_renamer
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt, OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.typedef import (TypeDef, GetSetProperty, descr_get_dict,
    descr_set_dict, descr_del_dict)
from pypy.objspace.std import unicodeobject
from pypy.objspace.std.floatobject import HASH_MODULUS, HASH_INF, HASH_NAN
from pypy.module._decimal import interp_context

VERSION = "1.7"
LIBMPDEC_VERSION = rffi.charp2str(rmpdec.mpd_version())

if HASH_MODULUS == 2**31 - 1:
    INVERSE_10_MODULUS = 1503238553
elif HASH_MODULUS == 2**61 - 1:
    INVERSE_10_MODULUS = 2075258708292324556
else:
    raise NotImplementedError('Unsupported HASH_MODULUS')
assert (INVERSE_10_MODULUS * 10) % HASH_MODULUS == 1


IEEE_CONTEXT_MAX_BITS = rmpdec.MPD_IEEE_CONTEXT_MAX_BITS
MAX_PREC = rmpdec.MPD_MAX_PREC
MAX_EMAX = rmpdec.MPD_MAX_EMAX
MIN_EMIN = rmpdec.MPD_MIN_EMIN
MIN_ETINY = rmpdec.MPD_MIN_ETINY

# DEC_MINALLOC >= MPD_MINALLOC
DEC_MINALLOC = 4

class State:
    def __init__(self, space):
        w_import = space.builtin.get('__import__')
        w_numbers = space.call_function(w_import,
                                        space.wrap('numbers'))
        self.w_Rational = space.getattr(w_numbers,
                                        space.wrap('Rational'))


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

    def descr_hash(self, space):
        if rmpdec.mpd_isspecial(self.mpd):
            if rmpdec.mpd_issnan(self.mpd):
                raise oefmt(space.w_TypeError,
                            "cannot hash a signaling NaN value")
            elif rmpdec.mpd_isnan(self.mpd):
                return space.wrap(HASH_NAN)
            elif rmpdec.mpd_isnegative(self.mpd):
                return space.wrap(-HASH_INF)
            else:
                return space.wrap(HASH_INF)

        with lltype.scoped_alloc(rffi.CArrayPtr(rffi.UINT).TO, 1,
                                 zero=True) as status_ptr:
            with lltype.scoped_alloc(rmpdec.MPD_CONTEXT_PTR.TO) as ctx:
                rmpdec.mpd_maxcontext(ctx)

                # XXX cache these
                w_p = W_Decimal.allocate(space)
                rmpdec.mpd_qset_ssize(w_p.mpd, HASH_MODULUS,
                                      ctx, status_ptr)
                w_ten = W_Decimal.allocate(space)
                rmpdec.mpd_qset_ssize(w_ten.mpd, 10,
                                      ctx, status_ptr)
                w_inv10_p = W_Decimal.allocate(space)
                rmpdec.mpd_qset_ssize(w_inv10_p.mpd, INVERSE_10_MODULUS,
                                      ctx, status_ptr)


                w_exp_hash = W_Decimal.allocate(space)
                w_tmp = W_Decimal.allocate(space)
                exp = self.mpd.c_exp
                if exp >= 0:
                    # 10**exp(v) % p
                    rmpdec.mpd_qsset_ssize(w_tmp.mpd, exp, ctx, status_ptr)
                    rmpdec.mpd_qpowmod(
                        w_exp_hash.mpd, w_ten.mpd, w_tmp.mpd, w_p.mpd,
                        ctx, status_ptr)
                else:
                    # inv10_p**(-exp(v)) % p
                    rmpdec.mpd_qsset_ssize(w_tmp.mpd, -exp, ctx, status_ptr)
                    rmpdec.mpd_qpowmod(
                        w_exp_hash.mpd, w_inv10_p.mpd, w_tmp.mpd, w_p.mpd,
                        ctx, status_ptr)
                # hash = (int(v) * exp_hash) % p
                rmpdec.mpd_qcopy(w_tmp.mpd, self.mpd, status_ptr)
                w_tmp.mpd.c_exp = 0
                rmpdec.mpd_set_positive(w_tmp.mpd)

                ctx.c_prec = rmpdec.MPD_MAX_PREC + 21
                ctx.c_emax = rmpdec.MPD_MAX_EMAX + 21
                ctx.c_emin = rmpdec.MPD_MIN_EMIN - 21

                rmpdec.mpd_qmul(w_tmp.mpd, w_tmp.mpd, w_exp_hash.mpd,
                                ctx, status_ptr)
                rmpdec.mpd_qrem(w_tmp.mpd, w_tmp.mpd, w_p.mpd,
                                ctx, status_ptr)

                result = rmpdec.mpd_qget_ssize(w_tmp.mpd, status_ptr);
                if rmpdec.mpd_isnegative(self.mpd):
                    result = -result
                if result == -1:
                    result = -2
            status = rffi.cast(lltype.Signed, status_ptr[0])
        if status:
            if status & rmpdec.MPD_Malloc_error:
                raise OperationError(space.w_MemoryError, space.w_None)
            else:
                raise OperationError(space.w_SystemError, space.wrap(
                        "Decimal.__hash__ internal error; please report"))
        return space.wrap(result)

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

    def to_long(self, space, context, round):
        if rmpdec.mpd_isspecial(self.mpd):
            if rmpdec.mpd_isnan(self.mpd):
                raise oefmt(space.w_ValueError,
                            "cannot convert NaN to integer")
            else:
                raise oefmt(space.w_OverflowError,
                            "cannot convert Infinity to integer")

        w_x = W_Decimal.allocate(space)
        w_tempctx = context.copy_w(space)
        rffi.setintfield(w_tempctx.ctx, 'c_round', round)
        with context.catch_status(space) as (ctx, status_ptr):
            # We round with the temporary context, but set status and
            # raise errors on the global one.
            rmpdec.mpd_qround_to_int(w_x.mpd, self.mpd,
                                     w_tempctx.ctx, status_ptr)

            # XXX mpd_qexport_u64 would be faster...
            T = rffi.CArrayPtr(rffi.USHORTP).TO
            with lltype.scoped_alloc(T, 1, zero=True) as digits_ptr:
                n = rmpdec.mpd_qexport_u16(
                    digits_ptr, 0, 0x10000,
                    w_x.mpd, status_ptr)
                if n == rmpdec.MPD_SIZE_MAX:
                    raise OperationError(space.w_MemoryError, space.w_None)
                try:
                    char_ptr = rffi.cast(rffi.CCHARP, digits_ptr[0])
                    size = rffi.cast(lltype.Signed, n) * 2
                    s = rffi.charpsize2str(char_ptr, size)
                finally:
                    rmpdec.mpd_free(digits_ptr[0])
            bigint = rbigint.rbigint.frombytes(
                s, byteorder=rbigint.BYTEORDER, signed=False)
        if rmpdec.mpd_isnegative(w_x.mpd) and not rmpdec.mpd_iszero(w_x.mpd):
            bigint = bigint.neg()
        return space.newlong_from_rbigint(bigint)

    def descr_int(self, space):
        context = interp_context.getcontext(space)
        return self.to_long(space, context, rmpdec.MPD_ROUND_DOWN)
        
    def descr_trunc(self, space):
        context = interp_context.getcontext(space)
        return self.to_long(space, context, rmpdec.MPD_ROUND_DOWN)
        
    def descr_floor(self, space):
        context = interp_context.getcontext(space)
        return self.to_long(space, context, rmpdec.MPD_ROUND_FLOOR)
        
    def descr_ceil(self, space):
        context = interp_context.getcontext(space)
        return self.to_long(space, context, rmpdec.MPD_ROUND_CEILING)

    def descr_round(self, space, w_x=None):
        context = interp_context.getcontext(space)
        if not w_x:
            return self.to_long(space, context, rmpdec.MPD_ROUND_HALF_EVEN)
        x = space.int_w(w_x)
        w_result = W_Decimal.allocate(space)
        w_q = decimal_from_ssize(space, None, 1, context, exact=False)
        if x == rmpdec.MPD_SSIZE_MIN:
            w_q.mpd.c_exp = rmpdec.MPD_SSIZE_MAX
        else:
            w_q.mpd.c_exp = -x
        with context.catch_status(space) as (ctx, status_ptr):
            rmpdec.mpd_qquantize(w_result.mpd, self.mpd, w_q.mpd,
                                 ctx, status_ptr)
        return w_result

    def _recode_to_utf8(self, ptr):
        s = rffi.charp2str(ptr)
        if len(s) == 0 or (len(s) == 1 and 32 <= ord(s[0]) < 128):
            return None, ptr
        # XXX use mbstowcs()
        s = s
        ptr = rffi.str2charp(s)
        return ptr, ptr

    @unwrap_spec(fmt=unicode)
    def descr_format(self, space, fmt, w_override=None):
        fmt = fmt.encode('utf-8')
        context = interp_context.getcontext(space)

        replace_fillchar = False 
        if fmt and fmt[0] == '\0':
            # NUL fill character: must be replaced with a valid UTF-8 char
            # before calling mpd_parse_fmt_str().
            replace_fillchar = True
            fmt = '_' + fmt[1:]

        dot_buf = sep_buf = grouping_buf = lltype.nullptr(rffi.CCHARP.TO)
        spec = lltype.malloc(rmpdec.MPD_SPEC_PTR.TO, flavor='raw')
        try:
            if not rmpdec.mpd_parse_fmt_str(spec, fmt, context.capitals):
                raise oefmt(space.w_ValueError, "invalid format string")
            if replace_fillchar:
                # In order to avoid clobbering parts of UTF-8 thousands
                # separators or decimal points when the substitution is
                # reversed later, the actual placeholder must be an invalid
                # UTF-8 byte.
                spec.c_fill[0] = '\xff'
                spec.c_fill[1] = '\0'

            if w_override:
                # Values for decimal_point, thousands_sep and grouping can
                # be explicitly specified in the override dict. These values
                # take precedence over the values obtained from localeconv()
                # in mpd_parse_fmt_str(). The feature is not documented and
                # is only used in test_decimal.
                try:
                    w_dot = space.getitem(
                        w_override, space.wrap("decimal_point"))
                except OperationError as e:
                    if not e.match(space, space.w_KeyError):
                        raise
                else:
                    dot_buf = rffi.str2charp(space.str_w(w_dot))
                    spec.c_dot = dot_buf
                try:
                    w_sep = space.getitem(
                        w_override, space.wrap("thousands_sep"))
                except OperationError as e:
                    if not e.match(space, space.w_KeyError):
                        raise
                else:
                    sep_buf = rffi.str2charp(space.str_w(w_sep))
                    spec.c_sep = sep_buf
                try:
                    w_grouping = space.getitem(
                        w_override, space.wrap("grouping"))
                except OperationError as e:
                    if not e.match(space, space.w_KeyError):
                        raise
                else:
                    grouping_buf = rffi.str2charp(space.str_w(w_grouping))
                    spec.c_grouping = grouping_buf
                if rmpdec.mpd_validate_lconv(spec) < 0:
                    raise oefmt(space.w_ValueError, "invalid override dict")
            else:
                dot_buf, spec.c_dot = self._recode_to_utf8(spec.c_dot)
                sep_buf, spec.c_sep = self._recode_to_utf8(spec.c_sep)

            with context.catch_status(space) as (ctx, status_ptr):
                decstring = rmpdec.mpd_qformat_spec(
                    self.mpd, spec, context.ctx, status_ptr)
                status = rffi.cast(lltype.Signed, status_ptr[0])
            if not decstring:
                if status & rmpdec.MPD_Malloc_error:
                    raise OperationError(space.w_MemoryError, space.w_None)
                else:
                    raise oefmt(space.w_ValueError,
                                "format specification exceeds "
                                "internal limits of _decimal")
        finally:
            lltype.free(spec, flavor='raw')
            if dot_buf:
                lltype.free(dot_buf, flavor='raw')
            if sep_buf:
                lltype.free(sep_buf, flavor='raw')
            if grouping_buf:
                lltype.free(grouping_buf, flavor='raw')

        ret = rffi.charp2str(decstring)
        if replace_fillchar:
            ret = ret.replace('\xff', '\0')
        return space.wrap(ret.decode('utf-8'))

    def compare(self, space, w_other, op):
        context = interp_context.getcontext(space)
        w_err, w_self, w_other = convert_binop_cmp(
            space, context, op, self, w_other)
        if w_err:
            return w_err
        with lltype.scoped_alloc(rffi.CArrayPtr(rffi.UINT).TO, 1,
                                 zero=True) as status_ptr:
            r = rmpdec.mpd_qcmp(w_self.mpd, w_other.mpd, status_ptr)

            if r > 0xFFFF:
                # sNaNs or op={le,ge,lt,gt} always signal.
                if (rmpdec.mpd_issnan(w_self.mpd) or
                    rmpdec.mpd_issnan(w_other.mpd) or
                    op not in ('eq', 'ne')):
                    status = rffi.cast(lltype.Signed, status_ptr[0])
                    context.addstatus(space, status)
                # qNaN comparison with op={eq,ne} or comparison with
                # InvalidOperation disabled.
                if op == 'ne':
                    return space.w_True
                else:
                    return space.w_False

        if op == 'eq':
            return space.wrap(r == 0)
        elif op == 'ne':
            return space.wrap(r != 0)
        elif op == 'le':
            return space.wrap(r <= 0)
        elif op == 'ge':
            return space.wrap(r >= 0)
        elif op == 'lt':
            return space.wrap(r == -1)
        elif op == 'gt':
            return space.wrap(r == 1)
        else:
            return space.w_NotImplemented

    def descr_eq(self, space, w_other):
        return self.compare(space, w_other, 'eq')
    def descr_ne(self, space, w_other):
        return self.compare(space, w_other, 'ne')
    def descr_lt(self, space, w_other):
        return self.compare(space, w_other, 'lt')
    def descr_le(self, space, w_other):
        return self.compare(space, w_other, 'le')
    def descr_gt(self, space, w_other):
        return self.compare(space, w_other, 'gt')
    def descr_ge(self, space, w_other):
        return self.compare(space, w_other, 'ge')

    # Binary operations
    @staticmethod
    def divmod_impl(space, context, w_x, w_y):
        w_err, w_a, w_b = convert_binop(space, context, w_x, w_y)
        if w_err:
            return w_err
        w_q = W_Decimal.allocate(space)
        w_r = W_Decimal.allocate(space)
        with context.catch_status(space) as (ctx, status_ptr):
            rmpdec.mpd_qdivmod(w_q.mpd, w_r.mpd, w_a.mpd, w_b.mpd,
                               ctx, status_ptr)
        return space.newtuple([w_q, w_r])

    def descr_divmod(self, space, w_other):
        context = interp_context.getcontext(space)
        return W_Decimal.divmod_impl(space, context, self, w_other)
    def descr_rdivmod(self, space, w_other):
        context = interp_context.getcontext(space)
        return W_Decimal.divmod_impl(space, context, w_other, self)

    @staticmethod
    def pow_impl(space, w_base, w_exp, w_mod):
        context = interp_context.getcontext(space)

        w_err, w_a, w_b = convert_binop(space, context, w_base, w_exp)
        if w_err:
            return w_err

        if not space.is_none(w_mod):
            w_err, w_c = convert_op(space, context, w_mod)
            if w_err:
                return w_err
        else:
            w_c = None
        w_result = W_Decimal.allocate(space)
        with context.catch_status(space) as (ctx, status_ptr):
            if w_c:
                rmpdec.mpd_qpowmod(w_result.mpd, w_a.mpd, w_b.mpd, w_c.mpd,
                                   ctx, status_ptr)
            else:
                rmpdec.mpd_qpow(w_result.mpd, w_a.mpd, w_b.mpd,
                                ctx, status_ptr)
        return w_result

    def descr_pow(self, space, w_other, w_mod=None):
        return W_Decimal.pow_impl(space, self, w_other, w_mod)
    def descr_rpow(self, space, w_other):
        return W_Decimal.pow_impl(space, w_other, self, None)

    def copy_abs_w(self, space):
        w_result = W_Decimal.allocate(space)
        with lltype.scoped_alloc(rffi.CArrayPtr(rffi.UINT).TO, 1,
                                 zero=True) as status_ptr:
            rmpdec.mpd_qcopy_abs(w_result.mpd, self.mpd, status_ptr)
            status = rffi.cast(lltype.Signed, status_ptr[0])
        if status & rmpdec.MPD_Malloc_error:
            raise OperationError(space.w_MemoryError, space.w_None)
        return w_result

    def copy_negate_w(self, space):
        w_result = W_Decimal.allocate(space)
        with lltype.scoped_alloc(rffi.CArrayPtr(rffi.UINT).TO, 1,
                                 zero=True) as status_ptr:
            rmpdec.mpd_qcopy_negate(w_result.mpd, self.mpd, status_ptr)
            status = rffi.cast(lltype.Signed, status_ptr[0])
        if status & rmpdec.MPD_Malloc_error:
            raise OperationError(space.w_MemoryError, space.w_None)
        return w_result

    def copy_sign_w(self, space, w_other, w_context=None):
        context = convert_context(space, w_context)
        w_other = convert_op_raise(space, context, w_other)
        w_result = W_Decimal.allocate(space)
        with context.catch_status(space) as (ctx, status_ptr):
            rmpdec.mpd_qcopy_sign(w_result.mpd, self.mpd, w_other.mpd,
                                  status_ptr)
        return w_result

    # Unary arithmetic functions, optional context arg

    def number_class_w(self, space, w_context=None):
        context = interp_context.ensure_context(space, w_context)
        cp = rmpdec.mpd_class(self.mpd, context.ctx)
        return space.wrap(rffi.charp2str(cp))

    def to_integral_w(self, space, w_rounding=None, w_context=None):
        context = interp_context.ensure_context(space, w_context)
        w_workctx = context.copy_w(space)
        if not space.is_none(w_rounding):
            w_workctx.set_rounding(space, w_rounding)
        w_result = W_Decimal.allocate(space)
        with context.catch_status(space) as (ctx, status_ptr):
            # We round with the temporary context, but set status and
            # raise errors on the global one.
            rmpdec.mpd_qround_to_int(w_result.mpd, self.mpd,
                                     w_workctx.ctx, status_ptr)
        return w_result
        
    def to_integral_exact_w(self, space, w_rounding=None, w_context=None):
        context = interp_context.ensure_context(space, w_context)
        w_workctx = context.copy_w(space)
        if not space.is_none(w_rounding):
            w_workctx.set_rounding(space, w_rounding)
        w_result = W_Decimal.allocate(space)
        with context.catch_status(space) as (ctx, status_ptr):
            # We round with the temporary context, but set status and
            # raise errors on the global one.
            rmpdec.mpd_qround_to_intx(w_result.mpd, self.mpd,
                                      w_workctx.ctx, status_ptr)
        return w_result

    # Ternary arithmetic functions, optional context arg
    def fma_w(self, space, w_other, w_third, w_context=None):
        context = interp_context.ensure_context(space, w_context)
        w_a, w_b, w_c = convert_ternop_raise(space, context,
                                             self, w_other, w_third)
        w_result = W_Decimal.allocate(space)
        with context.catch_status(space) as (ctx, status_ptr):
            rmpdec.mpd_qfma(w_result.mpd, w_a.mpd, w_b.mpd, w_c.mpd,
                            ctx, status_ptr)
        return w_result
        
    # Boolean functions
    def is_canonical_w(self, space):
        return space.wrap(bool(rmpdec.mpd_iscanonical(self.mpd)))
    def is_nan_w(self, space):
        return space.wrap(bool(rmpdec.mpd_isnan(self.mpd)))
    def is_qnan_w(self, space):
        return space.wrap(bool(rmpdec.mpd_isqnan(self.mpd)))
    def is_snan_w(self, space):
        return space.wrap(bool(rmpdec.mpd_issnan(self.mpd)))
    def is_infinite_w(self, space):
        return space.wrap(bool(rmpdec.mpd_isinfinite(self.mpd)))
    def is_finite_w(self, space):
        return space.wrap(bool(rmpdec.mpd_isfinite(self.mpd)))
    def is_signed_w(self, space):
        return space.wrap(bool(rmpdec.mpd_issigned(self.mpd)))
    def is_zero_w(self, space):
        return space.wrap(bool(rmpdec.mpd_iszero(self.mpd)))
    # Boolean functions, optional context arg
    def is_normal_w(self, space, w_context=None):
        context = interp_context.ensure_context(space, w_context)
        return space.wrap(bool(rmpdec.mpd_isnormal(self.mpd, context.ctx)))
    def is_subnormal_w(self, space, w_context=None):
        context = interp_context.ensure_context(space, w_context)
        return space.wrap(bool(rmpdec.mpd_issubnormal(self.mpd, context.ctx)))

    def as_tuple_w(self, space):
        "Return the DecimalTuple representation of a Decimal"
        w_sign = space.wrap(rmpdec.mpd_sign(self.mpd))
        if rmpdec.mpd_isinfinite(self.mpd):
            w_expt = space.wrap("F")
            # decimal.py has non-compliant infinity payloads.
            w_coeff = space.newtuple([space.wrap(0)])
        else:
            if rmpdec.mpd_isnan(self.mpd):
                if rmpdec.mpd_issnan(self.mpd):
                    w_expt = space.wrap("N")
                else:
                    w_expt = space.wrap("n")
            else:
                w_expt = space.wrap(self.mpd.c_exp)

            if self.mpd.c_len > 0:
                # coefficient is defined

                # make an integer
                # XXX this should be done in C...
                x = rmpdec.mpd_qncopy(self.mpd)
                if not x:
                    raise OperationError(space.w_MemoryError, space.w_None)
                try:
                    x.c_exp = 0
                    # clear NaN and sign
                    rmpdec.mpd_clear_flags(x)
                    intstring = rmpdec.mpd_to_sci(x, 1)
                finally:
                    rmpdec.mpd_del(x)
                if not intstring:
                    raise OperationError(space.w_MemoryError, space.w_None)
                try:
                    digits = rffi.charp2str(intstring)
                finally:
                    rmpdec.mpd_free(intstring)
                w_coeff = space.newtuple([
                        space.wrap(ord(d) - ord('0'))
                        for d in digits])
            else:
                w_coeff = space.newtuple([])

        return space.call_function(
            interp_context.state_get(space).W_DecimalTuple,
            w_sign, w_coeff, w_expt)


# Helper functions for arithmetic conversions
def convert_op(space, context, w_value):
    if isinstance(w_value, W_Decimal):
        return None, w_value
    elif space.isinstance_w(w_value, space.w_int):
        value = space.bigint_w(w_value)
        return None, decimal_from_bigint(space, None, value, context,
                                         exact=True)
    return space.w_NotImplemented, None

def convert_op_raise(space, context, w_x):
    w_err, w_a = convert_op(space, context, w_x)
    if w_err:
        raise oefmt(space.w_TypeError,
                    "conversion from %N to Decimal is not supported",
                    space.type(w_x))
    return w_a

def convert_binop(space, context, w_x, w_y):
    w_err, w_a = convert_op(space, context, w_x)
    if w_err:
        return w_err, None, None
    w_err, w_b = convert_op(space, context, w_y)
    if w_err:
        return w_err, None, None
    return None, w_a, w_b

def convert_binop_raise(space, context, w_x, w_y):
    w_err, w_a = convert_op(space, context, w_x)
    if w_err:
        raise oefmt(space.w_TypeError,
                    "conversion from %N to Decimal is not supported",
                    space.type(w_x))
    w_err, w_b = convert_op(space, context, w_y)
    if w_err:
        raise oefmt(space.w_TypeError,
                    "conversion from %N to Decimal is not supported",
                    space.type(w_y))
    return w_a, w_b

def convert_ternop_raise(space, context, w_x, w_y, w_z):
    w_err, w_a = convert_op(space, context, w_x)
    if w_err:
        raise oefmt(space.w_TypeError,
                    "conversion from %N to Decimal is not supported",
                    space.type(w_x))
    w_err, w_b = convert_op(space, context, w_y)
    if w_err:
        raise oefmt(space.w_TypeError,
                    "conversion from %N to Decimal is not supported",
                    space.type(w_y))
    w_err, w_c = convert_op(space, context, w_z)
    if w_err:
        raise oefmt(space.w_TypeError,
                    "conversion from %N to Decimal is not supported",
                    space.type(w_z))
    return w_a, w_b, w_c

# Convert rationals for comparison
def _multiply_by_denominator(space, w_v, w_r, context):
    # w_v is not special, w_r is a rational.
    w_denom = space.getattr(w_r, space.wrap("denominator"))
    denom = decimal_from_bigint(space, None, space.bigint_w(w_denom),
                                context, exact=True)
    vv = rmpdec.mpd_qncopy(w_v.mpd)
    if not vv:
        raise OperationError(space.w_MemoryError, space.w_None)
    try:
        w_result = W_Decimal.allocate(space)
        with lltype.scoped_alloc(rmpdec.MPD_CONTEXT_PTR.TO) as maxctx:
            rmpdec.mpd_maxcontext(maxctx)
            # Prevent Overflow in the following multiplication. The
            # result of the multiplication is only used in mpd_qcmp,
            # which can handle values that are technically out of
            # bounds, like (for 32-bit)
            # 99999999999999999999...99999999e+425000000.
            exp = vv.c_exp
            vv.c_exp = 0
            with lltype.scoped_alloc(rffi.CArrayPtr(rffi.UINT).TO, 1,
                                     zero=True) as status_ptr:
                rmpdec.mpd_qmul(w_result.mpd, vv, denom.mpd, maxctx, status_ptr)
                # If any status has been accumulated during the multiplication,
                # the result is invalid. This is very unlikely, since even the
                # 32-bit version supports 425000000 digits.
                status = rffi.cast(lltype.Signed, status_ptr[0])
            if status:
                raise oefmt(space.w_ValueError,
                            "exact conversion for comparison failed")
            w_result.mpd.c_exp = exp
    finally:
        rmpdec.mpd_del(vv)

    return w_result

def _numerator_as_decimal(space, w_r, context):
    w_numerator = space.getattr(w_r, space.wrap("numerator"))
    return decimal_from_bigint(space, None, space.bigint_w(w_numerator),
                               context, exact=True)

def convert_binop_cmp(space, context, op, w_v, w_w):
    if isinstance(w_w, W_Decimal):
        return None, w_v, w_w
    elif space.isinstance_w(w_w, space.w_int):
        value = space.bigint_w(w_w)
        w_w = decimal_from_bigint(space, None, value, context,
                                  exact=True)
        return None, w_v, w_w
    elif space.isinstance_w(w_w, space.w_float):
        if op not in ('eq', 'ne'):
            # Add status, and maybe raise
            context.addstatus(space, rmpdec.MPD_Float_operation)
        else:
            # Add status, but don't raise
            new_status = (rmpdec.MPD_Float_operation |
                          rffi.cast(lltype.Signed, context.ctx.c_status))
            context.ctx.c_status = rffi.cast(rffi.UINT, new_status)
        w_w = decimal_from_float(space, None, w_w, context, exact=True)
    elif space.isinstance_w(w_w, space.w_complex):
        if op not in ('eq', 'ne'):
            return space.w_NotImplemented, None, None
        real, imag = space.unpackcomplex(w_w)
        if imag == 0.0:
            # Add status, but don't raise
            new_status = (rmpdec.MPD_Float_operation |
                          rffi.cast(lltype.Signed, context.ctx.c_status))
            context.ctx.c_status = rffi.cast(rffi.UINT, new_status)
            w_w = decimal_from_float(space, None, w_w, context, exact=True)
        else:
            return space.w_NotImplemented, None, None
    elif space.isinstance_w(w_w, space.fromcache(State).w_Rational):
        w_numerator = _numerator_as_decimal(space, w_w, context)
        if not rmpdec.mpd_isspecial(w_v.mpd):
            w_v = _multiply_by_denominator(space, w_v, w_w, context)
        w_w = w_numerator
    else:
        return space.w_NotImplemented, None, None
    return None, w_v, w_w


def make_unary_number_method(mpd_func_name):
    mpd_func = getattr(rmpdec, mpd_func_name)
    @func_renamer('descr_%s' % mpd_func_name)
    def descr_method(space, w_self):
        self = space.interp_w(W_Decimal, w_self)
        context = interp_context.getcontext(space)
        w_result = W_Decimal.allocate(space)
        with context.catch_status(space) as (ctx, status_ptr):
            mpd_func(w_result.mpd, self.mpd, ctx, status_ptr)
        return w_result
    return interp2app(descr_method)

def binary_number_method(space, mpd_func, w_x, w_y):
    context = interp_context.getcontext(space)

    w_err, w_a, w_b = convert_binop(space, context, w_x, w_y)
    if w_err:
        return w_err
    w_result = W_Decimal.allocate(space)
    with context.catch_status(space) as (ctx, status_ptr):
        mpd_func(w_result.mpd, w_a.mpd, w_b.mpd, ctx, status_ptr)
    return w_result

def make_binary_number_method(mpd_func_name):
    mpd_func = getattr(rmpdec, mpd_func_name)
    @func_renamer('descr_%s' % mpd_func_name)
    def descr_method(space, w_self, w_other):
        return binary_number_method(space, mpd_func, w_self, w_other)
    return interp2app(descr_method)

def make_binary_number_method_right(mpd_func_name):
    mpd_func = getattr(rmpdec, mpd_func_name)
    @func_renamer('descr_r_%s' % mpd_func_name)
    def descr_method(space, w_self, w_other):
        return binary_number_method(space, mpd_func, w_other, w_self)
    return interp2app(descr_method)

# Unary function with an optional context arg.
def unary_method(space, mpd_func, w_self, w_context):
    self = space.interp_w(W_Decimal, w_self)
    context = convert_context(space, w_context)
    w_result = W_Decimal.allocate(space)
    with context.catch_status(space) as (ctx, status_ptr):
        mpd_func(w_result.mpd, self.mpd, ctx, status_ptr)
    return w_result
    
def make_unary_method(mpd_func_name):
    mpd_func = getattr(rmpdec, mpd_func_name)
    @func_renamer('descr_%s' % mpd_func_name)
    def descr_method(space, w_self, w_context=None):
        return unary_method(space, mpd_func, w_self, w_context)
    return interp2app(descr_method)

# Binary function with an optional context arg.
def binary_method(space, mpd_func, w_self, w_other, w_context):
    self = space.interp_w(W_Decimal, w_self)
    context = convert_context(space, w_context)
    w_a, w_b = convert_binop_raise(space, context, w_self, w_other)
    w_result = W_Decimal.allocate(space)
    with context.catch_status(space) as (ctx, status_ptr):
        mpd_func(w_result.mpd, w_a.mpd, w_b.mpd, ctx, status_ptr)
    return w_result
    
def make_binary_method(mpd_func_name):
    mpd_func = getattr(rmpdec, mpd_func_name)
    @func_renamer('descr_%s' % mpd_func_name)
    def descr_method(space, w_self, w_other, w_context=None):
        return binary_method(space, mpd_func, w_self, w_other, w_context)
    return interp2app(descr_method)

def convert_context(space, w_context):
    if space.is_none(w_context):
        return interp_context.getcontext(space)
    return space.interp_w(interp_context.W_Context, w_context)

def decimal_from_float_w(space, w_cls, w_float):
    context = interp_context.getcontext(space)
    return decimal_from_float(space, w_cls, w_float, context, exact=True)

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
        sign = space.int_w(w_sign, allow_conversion=False)
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
    if space.isinstance_w(w_value, space.w_int):
        value = space.bigint_w(w_value)
        return decimal_from_bigint(space, w_subtype, value, context,
                                   exact=exact)
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
    __hash__ = interp2app(W_Decimal.descr_hash),
    __bool__ = interp2app(W_Decimal.descr_bool),
    __float__ = interp2app(W_Decimal.descr_float),
    __int__ = interp2app(W_Decimal.descr_int),
    __trunc__ = interp2app(W_Decimal.descr_trunc),
    __floor__ = interp2app(W_Decimal.descr_floor),
    __ceil__ = interp2app(W_Decimal.descr_ceil),
    __round__ = interp2app(W_Decimal.descr_round),
    __format__ = interp2app(W_Decimal.descr_format),
    #
    __eq__ = interp2app(W_Decimal.descr_eq),
    __ne__ = interp2app(W_Decimal.descr_ne),
    __le__ = interp2app(W_Decimal.descr_le),
    __ge__ = interp2app(W_Decimal.descr_ge),
    __lt__ = interp2app(W_Decimal.descr_lt),
    __gt__ = interp2app(W_Decimal.descr_gt),
    # Unary operations
    __pos__ = make_unary_number_method('mpd_qplus'),
    __neg__ = make_unary_number_method('mpd_qminus'),
    __abs__ = make_unary_number_method('mpd_qabs'),
    # Binary operations
    __add__ = make_binary_number_method('mpd_qadd'),
    __sub__ = make_binary_number_method('mpd_qsub'),
    __mul__ = make_binary_number_method('mpd_qmul'),
    __truediv__ = make_binary_number_method('mpd_qdiv'),
    __floordiv__ = make_binary_number_method('mpd_qdivint'),
    __mod__ = make_binary_number_method('mpd_qrem'),
    __divmod__ = interp2app(W_Decimal.descr_divmod),
    __pow__ = interp2app(W_Decimal.descr_pow),
    #
    __radd__ = make_binary_number_method_right('mpd_qadd'),
    __rsub__ = make_binary_number_method_right('mpd_qsub'),
    __rmul__ = make_binary_number_method_right('mpd_qmul'),
    __rtruediv__ = make_binary_number_method_right('mpd_qdiv'),
    __rfloordiv__ = make_binary_number_method_right('mpd_qdivint'),
    __rmod__ = make_binary_number_method_right('mpd_qrem'),
    __rdivmod__ = interp2app(W_Decimal.descr_rdivmod),
    __rpow__ = interp2app(W_Decimal.descr_rpow),
    # Unary functions, optional context arg for conversion errors
    copy_abs = interp2app(W_Decimal.copy_abs_w),
    copy_negate = interp2app(W_Decimal.copy_negate_w),
    # Unary arithmetic functions, optional context arg
    exp = make_unary_method('mpd_qexp'),
    ln = make_unary_method('mpd_qln'),
    log10 = make_unary_method('mpd_qlog10'),
    logb = make_unary_method('mpd_qlogb'),
    logical_invert = make_unary_method('mpd_qinvert'),
    next_minus = make_unary_method('mpd_qnext_minus'),
    next_plus = make_unary_method('mpd_qnext_plus'),
    normalize = make_unary_method('mpd_qreduce'),
    number_class = interp2app(W_Decimal.number_class_w),
    to_integral = interp2app(W_Decimal.to_integral_w),
    to_integral_exact = interp2app(W_Decimal.to_integral_exact_w),
    to_integral_value = interp2app(W_Decimal.to_integral_w),
    sqrt = make_unary_method('mpd_qsqrt'),
    # Binary arithmetic functions, optional context arg
    compare = make_binary_method('mpd_qcompare'),
    compare_signal = make_binary_method('mpd_qcompare_signal'),
    # Ternary arithmetic functions, optional context arg
    fma = interp2app(W_Decimal.fma_w),
    # Boolean functions, no context arg
    is_canonical = interp2app(W_Decimal.is_canonical_w),
    is_nan = interp2app(W_Decimal.is_nan_w),
    is_qnan = interp2app(W_Decimal.is_qnan_w),
    is_snan = interp2app(W_Decimal.is_snan_w),
    is_infinite = interp2app(W_Decimal.is_infinite_w),
    is_finite = interp2app(W_Decimal.is_finite_w),
    is_signed = interp2app(W_Decimal.is_signed_w),
    is_zero = interp2app(W_Decimal.is_zero_w),
    # Boolean functions, optional context arg
    is_normal = interp2app(W_Decimal.is_normal_w),
    is_subnormal = interp2app(W_Decimal.is_subnormal_w),
    # Binary functions, optional context arg for conversion errors
    copy_sign = interp2app(W_Decimal.copy_sign_w),
    #
    as_tuple = interp2app(W_Decimal.as_tuple_w),
    from_float = interp2app(decimal_from_float_w, as_classmethod=True),
    )
