import sys, os, struct
from contextlib import contextmanager
from rpython.rlib import rarithmetic
from rpython.rlib.objectmodel import not_rpython, always_inline
from rpython.rlib.rgc import no_collect
from rpython.rlib.rarithmetic import r_uint64
from rpython.rlib.rawstorage import misaligned_is_fine
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop


if sys.byteorder == 'little':
    def _le64toh(x):
        return x
else:
    _le64toh = rarithmetic.byteswap


# Initialize the values of the secret seed: two 64-bit constants.
# CPython picks a new seed every time 'python' starts.  PyPy cannot do
# that as easily because many details may rely on getting the same hash
# value before and after translation.  We can, however, pick a random
# seed once per translation, which should already be quite good.
#
# XXX no, it is not: e.g. all Ubuntu installations of the same Ubuntu
# would get the same seed.  That's not good enough.

@not_rpython
def select_random_seed():
    global k0, k1    # note: the globals k0, k1 are already byte-swapped
    v0, v1 = struct.unpack("QQ", os.urandom(16))
    k0 = r_uint64(v0)
    k1 = r_uint64(v1)

select_random_seed()

@contextmanager
def choosen_seed(new_k0, new_k1, test_misaligned_path=False):
    global k0, k1, misaligned_is_fine
    old = k0, k1, misaligned_is_fine
    k0 = _le64toh(r_uint64(new_k0))
    k1 = _le64toh(r_uint64(new_k1))
    if test_misaligned_path:
        misaligned_is_fine = False
    yield
    k0, k1, misaligned_is_fine = old

def get_current_seed():
    return _le64toh(k0), _le64toh(k1)


magic0 = r_uint64(0x736f6d6570736575)
magic1 = r_uint64(0x646f72616e646f6d)
magic2 = r_uint64(0x6c7967656e657261)
magic3 = r_uint64(0x7465646279746573)


@always_inline
def _rotate(x, b):
    return (x << b) | (x >> (64 - b))

@always_inline
def _half_round(a, b, c, d, s, t):
    a += b
    c += d
    b = _rotate(b, s) ^ a
    d = _rotate(d, t) ^ c
    a = _rotate(a, 32)
    return a, b, c, d

@always_inline
def _double_round(v0, v1, v2, v3):
    v0,v1,v2,v3 = _half_round(v0,v1,v2,v3,13,16)
    v2,v1,v0,v3 = _half_round(v2,v1,v0,v3,17,21)
    v0,v1,v2,v3 = _half_round(v0,v1,v2,v3,13,16)
    v2,v1,v0,v3 = _half_round(v2,v1,v0,v3,17,21)
    return v0, v1, v2, v3


@no_collect
def siphash24(addr_in, size):
    """Takes an address pointer and a size.  Returns the hash as a r_uint64,
    which can then be casted to the expected type."""

    direct = (misaligned_is_fine or
                 (rffi.cast(lltype.Signed, addr_in) & 7) == 0)

    b = r_uint64(size) << 56
    v0 = k0 ^ magic0
    v1 = k1 ^ magic1
    v2 = k0 ^ magic2
    v3 = k1 ^ magic3

    index = 0
    if direct:
        while size >= 8:
            mi = llop.raw_load(rffi.ULONGLONG, addr_in, index)
            mi = _le64toh(mi)
            size -= 8
            index += 8
            v3 ^= mi
            v0, v1, v2, v3 = _double_round(v0, v1, v2, v3)
            v0 ^= mi
    else:
        while size >= 8:
            mi = (
                r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index)) |
                r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 1)) << 8 |
                r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 2)) << 16 |
                r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 3)) << 24 |
                r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 4)) << 32 |
                r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 5)) << 40 |
                r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 6)) << 48 |
                r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 7)) << 56
            )
            mi = _le64toh(mi)
            size -= 8
            index += 8
            v3 ^= mi
            v0, v1, v2, v3 = _double_round(v0, v1, v2, v3)
            v0 ^= mi

    t = r_uint64(0)
    if size == 7:
        t = r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 6)) << 48
        size = 6
    if size == 6:
        t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 5)) << 40
        size = 5
    if size == 5:
        t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 4)) << 32
        size = 4
    if size == 4:
        if direct:
            t |= r_uint64(llop.raw_load(rffi.UINT, addr_in, index))
            size = 0
        else:
            t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 3)) << 24
            size = 3
    if size == 3:
        t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 2)) << 16
        size = 2
    if size == 2:
        t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 1)) << 8
        size = 1
    if size == 1:
        t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index))
        size = 0
    assert size == 0

    b |= _le64toh(t)

    v3 ^= b
    v0, v1, v2, v3 = _double_round(v0, v1, v2, v3)
    v0 ^= b
    v2 ^= 0xff
    v0, v1, v2, v3 = _double_round(v0, v1, v2, v3)
    v0, v1, v2, v3 = _double_round(v0, v1, v2, v3)

    return (v0 ^ v1) ^ (v2 ^ v3)
