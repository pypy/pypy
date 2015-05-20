"""Functions and helpers for converting between dtypes"""

from rpython.rlib import jit
from rpython.rlib.rarithmetic import LONG_BIT
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import oefmt, OperationError

from pypy.module.micronumpy.base import W_NDimArray, convert_to_array
from pypy.module.micronumpy import constants as NPY
from .types import (
    Bool, ULong, Long, Float64, Complex64, UnicodeType, VoidType, ObjectType,
    promotion_table)
from .descriptor import (
    get_dtype_cache, as_dtype, is_scalar_w, variable_dtype, new_string_dtype,
    new_unicode_dtype)

@jit.unroll_safe
def result_type(space, __args__):
    args_w, kw_w = __args__.unpack()
    if kw_w:
        raise oefmt(space.w_TypeError,
            "result_type() takes no keyword arguments")
    if not args_w:
        raise oefmt(space.w_ValueError,
            "at least one array or dtype is required")
    arrays_w = []
    dtypes_w = []
    for w_arg in args_w:
        if isinstance(w_arg, W_NDimArray):
            arrays_w.append(w_arg)
        elif is_scalar_w(space, w_arg):
            w_scalar = as_scalar(space, w_arg)
            w_arr = W_NDimArray.from_scalar(space, w_scalar)
            arrays_w.append(w_arr)
        else:
            dtype = as_dtype(space, w_arg)
            dtypes_w.append(dtype)
    return find_result_type(space, arrays_w, dtypes_w)


def find_result_type(space, arrays_w, dtypes_w):
    # equivalent to PyArray_ResultType
    if len(arrays_w) == 1 and not dtypes_w:
        return arrays_w[0].get_dtype()
    elif not arrays_w and len(dtypes_w) == 1:
        return dtypes_w[0]
    result = None
    for w_array in arrays_w:
        result = find_binop_result_dtype(space, result, w_array.get_dtype())
    for dtype in dtypes_w:
        result = find_binop_result_dtype(space, result, dtype)
    return result


@unwrap_spec(casting=str)
def can_cast(space, w_from, w_totype, casting='safe'):
    try:
        target = as_dtype(space, w_totype, allow_None=False)
    except TypeError:
        raise oefmt(space.w_TypeError,
            "did not understand one of the types; 'None' not accepted")
    if isinstance(w_from, W_NDimArray):
        return space.wrap(can_cast_array(space, w_from, target, casting))
    elif is_scalar_w(space, w_from):
        w_scalar = as_scalar(space, w_from)
        w_arr = W_NDimArray.from_scalar(space, w_scalar)
        return space.wrap(can_cast_array(space, w_arr, target, casting))

    try:
        origin = as_dtype(space, w_from, allow_None=False)
    except TypeError:
        raise oefmt(space.w_TypeError,
            "did not understand one of the types; 'None' not accepted")
    return space.wrap(can_cast_type(space, origin, target, casting))

kind_ordering = {
    Bool.kind: 0, ULong.kind: 1, Long.kind: 2,
    Float64.kind: 4, Complex64.kind: 5,
    NPY.STRINGLTR: 6, NPY.STRINGLTR2: 6,
    UnicodeType.kind: 7, VoidType.kind: 8, ObjectType.kind: 9}

def can_cast_type(space, origin, target, casting):
    # equivalent to PyArray_CanCastTypeTo
    if casting == 'no':
        return origin.eq(space, target)
    elif casting == 'equiv':
        return origin.num == target.num and origin.elsize == target.elsize
    elif casting == 'unsafe':
        return True
    elif casting == 'same_kind':
        if origin.can_cast_to(target):
            return True
        if origin.kind in kind_ordering and target.kind in kind_ordering:
            return kind_ordering[origin.kind] <= kind_ordering[target.kind]
        return False
    else:  # 'safe'
        return origin.can_cast_to(target)

def can_cast_array(space, w_from, target, casting):
    # equivalent to PyArray_CanCastArrayTo
    origin = w_from.get_dtype()
    if w_from.is_scalar():
        return can_cast_scalar(
            space, origin, w_from.get_scalar_value(), target, casting)
    else:
        return can_cast_type(space, origin, target, casting)

def can_cast_scalar(space, from_type, value, target, casting):
    # equivalent to CNumPy's can_cast_scalar_to
    if from_type == target or casting == 'unsafe':
        return True
    if not from_type.is_number() or casting in ('no', 'equiv'):
        return can_cast_type(space, from_type, target, casting)
    if not from_type.is_native():
        value = value.descr_byteswap(space)
    dtypenum, altnum = value.min_dtype()
    if target.is_unsigned():
        dtypenum = altnum
    dtype = get_dtype_cache(space).dtypes_by_num[dtypenum]
    return can_cast_type(space, dtype, target, casting)

def as_scalar(space, w_obj):
    dtype = find_dtype_for_scalar(space, w_obj)
    return dtype.coerce(space, w_obj)

def min_scalar_type(space, w_a):
    w_array = convert_to_array(space, w_a)
    dtype = w_array.get_dtype()
    if w_array.is_scalar() and dtype.is_number():
        num, alt_num = w_array.get_scalar_value().min_dtype()
        return get_dtype_cache(space).dtypes_by_num[num]
    else:
        return dtype

def promote_types(space, w_type1, w_type2):
    dt1 = as_dtype(space, w_type1, allow_None=False)
    dt2 = as_dtype(space, w_type2, allow_None=False)
    return _promote_types(space, dt1, dt2)

def find_binop_result_dtype(space, dt1, dt2):
    if dt2 is None:
        return dt1
    if dt1 is None:
        return dt2
    return _promote_types(space, dt1, dt2)

def _promote_types(space, dt1, dt2):
    num = promotion_table[dt1.num][dt2.num]
    if num != -1:
        return get_dtype_cache(space).dtypes_by_num[num]

    # dt1.num should be <= dt2.num
    if dt1.num > dt2.num:
        dt1, dt2 = dt2, dt1

    if dt2.is_str():
        if dt1.is_str():
            if dt1.elsize > dt2.elsize:
                return dt1
            else:
                return dt2
        else:  # dt1 is numeric
            dt1_size = dt1.itemtype.strlen
            if dt1_size > dt2.elsize:
                return new_string_dtype(space, dt1_size)
            else:
                return dt2
    elif dt2.is_unicode():
        if dt1.is_unicode():
            if dt1.elsize > dt2.elsize:
                return dt1
            else:
                return dt2
        elif dt1.is_str():
            if dt2.elsize >= 4 * dt1.elsize:
                return dt2
            else:
                return new_unicode_dtype(space, 4 * dt1.elsize)
        else:  # dt1 is numeric
            dt1_size = 4 * dt1.itemtype.strlen
            if dt1_size > dt2.elsize:
                return new_unicode_dtype(space, dt1_size)
            else:
                return dt2
    else:
        assert dt2.num == NPY.VOID
        if can_cast_type(space, dt1, dt2, casting='equiv'):
            return dt1
    raise oefmt(space.w_TypeError, "invalid type promotion")


def find_dtype_for_scalar(space, w_obj, current_guess=None):
    from .boxes import W_GenericBox
    bool_dtype = get_dtype_cache(space).w_booldtype
    long_dtype = get_dtype_cache(space).w_longdtype
    int64_dtype = get_dtype_cache(space).w_int64dtype
    uint64_dtype = get_dtype_cache(space).w_uint64dtype
    complex_dtype = get_dtype_cache(space).w_complex128dtype
    float_dtype = get_dtype_cache(space).w_float64dtype
    object_dtype = get_dtype_cache(space).w_objectdtype
    if isinstance(w_obj, W_GenericBox):
        dtype = w_obj.get_dtype(space)
        return find_binop_result_dtype(space, dtype, current_guess)

    if space.isinstance_w(w_obj, space.w_bool):
        return find_binop_result_dtype(space, bool_dtype, current_guess)
    elif space.isinstance_w(w_obj, space.w_int):
        return find_binop_result_dtype(space, long_dtype, current_guess)
    elif space.isinstance_w(w_obj, space.w_long):
        try:
            space.int_w(w_obj)
        except OperationError, e:
            if e.match(space, space.w_OverflowError):
                if space.is_true(space.le(w_obj, space.wrap(0))):
                    return find_binop_result_dtype(space, int64_dtype,
                                               current_guess)
                return find_binop_result_dtype(space, uint64_dtype,
                                               current_guess)
            raise
        return find_binop_result_dtype(space, int64_dtype, current_guess)
    elif space.isinstance_w(w_obj, space.w_float):
        return find_binop_result_dtype(space, float_dtype, current_guess)
    elif space.isinstance_w(w_obj, space.w_complex):
        return complex_dtype
    elif space.isinstance_w(w_obj, space.w_str):
        if current_guess is None:
            return variable_dtype(space, 'S%d' % space.len_w(w_obj))
        elif current_guess.num == NPY.STRING:
            if current_guess.elsize < space.len_w(w_obj):
                return variable_dtype(space, 'S%d' % space.len_w(w_obj))
        return current_guess
    return object_dtype
