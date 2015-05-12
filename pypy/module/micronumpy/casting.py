"""Functions and helpers for converting between dtypes"""

from rpython.rlib import jit
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import oefmt

from pypy.module.micronumpy.base import W_NDimArray, convert_to_array
from pypy.module.micronumpy import constants as NPY
from pypy.module.micronumpy.ufuncs import (
    find_binop_result_dtype, find_dtype_for_scalar)
from .types import (
    Bool, ULong, Long, Float64, Complex64, UnicodeType, VoidType, ObjectType)
from .descriptor import get_dtype_cache, as_dtype, is_scalar_w

@jit.unroll_safe
def result_type(space, __args__):
    args_w, kw_w = __args__.unpack()
    if kw_w:
        raise oefmt(space.w_TypeError,
            "result_type() takes no keyword arguments")
    if not args_w:
        raise oefmt(space.w_ValueError,
            "at least one array or dtype is required")
    result = None
    for w_arg in args_w:
        dtype = as_dtype(space, w_arg)
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
    else:
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
