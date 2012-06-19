from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import r_ulonglong


UNSIGNED = 0x1000

TYPES = [
    ("int8_t",        1),
    ("uint8_t",       1 | UNSIGNED),
    ("int16_t",       2),
    ("uint16_t",      2 | UNSIGNED),
    ("int32_t",       4),
    ("uint32_t",      4 | UNSIGNED),
    ("int64_t",       8),
    ("uint64_t",      8 | UNSIGNED),

    ("intptr_t",      rffi.sizeof(rffi.INTPTR_T)),
    ("uintptr_t",     rffi.sizeof(rffi.UINTPTR_T) | UNSIGNED),
    ("ptrdiff_t",     rffi.sizeof(rffi.INTPTR_T)),   # XXX can it be different?
    ("size_t",        rffi.sizeof(rffi.SIZE_T) | UNSIGNED),
    ("ssize_t",       rffi.sizeof(rffi.SSIZE_T)),
]


def nonstandard_integer_types(space):
    w_d = space.newdict()
    for name, size in TYPES:
        space.setitem(w_d, space.wrap(name), space.wrap(size))
    return w_d

# ____________________________________________________________

def as_long_long(space, w_ob, strict):
    # (possibly) convert and cast a Python object to a long long.
    # This version accepts a Python int too, and does convertions from
    # other types of objects.  It refuses floats.
    if space.is_w(space.type(w_ob), space.w_int):   # shortcut
        return space.int_w(w_ob)
    try:
        bigint = space.bigint_w(w_ob)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        if space.isinstance_w(w_ob, space.w_float):
            raise
        bigint = space.bigint_w(space.int(w_ob))
    try:
        return bigint.tolonglong()
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("long too big to convert"))

def as_unsigned_long_long(space, w_ob, strict):
    # (possibly) convert and cast a Python object to an unsigned long long.
    # This accepts a Python int too, and does convertions from other types of
    # objects.  If 'overflow', complains with OverflowError; if 'not overflow',
    # mask the result.
    if space.is_w(space.type(w_ob), space.w_int):   # shortcut
        value = space.int_w(w_ob)
        if strict and value < 0:
            raise OperationError(space.w_OverflowError, space.wrap(neg_msg))
        return r_ulonglong(value)
    try:
        bigint = space.bigint_w(w_ob)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        if strict and space.isinstance_w(w_ob, space.w_float):
            raise
        bigint = space.bigint_w(space.int(w_ob))
    if strict:
        try:
            return bigint.toulonglong()
        except ValueError:
            raise OperationError(space.w_OverflowError, space.wrap(neg_msg))
    else:
        return bigint.ulonglongmask()

neg_msg = "can't convert negative number to unsigned"
