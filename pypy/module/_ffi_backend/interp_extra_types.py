from pypy.rpython.lltypesystem import lltype, rffi


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
