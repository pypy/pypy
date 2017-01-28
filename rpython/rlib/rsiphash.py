import sys, os
from contextlib import contextmanager
from rpython.rlib import rarithmetic, rurandom
from rpython.rlib.objectmodel import not_rpython, always_inline
from rpython.rlib.objectmodel import we_are_translated, dont_inline
from rpython.rlib.rgc import no_collect
from rpython.rlib.rarithmetic import r_uint64, r_uint32, r_uint
from rpython.rlib.rawstorage import misaligned_is_fine
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop


if sys.byteorder == 'little':
    def _le64toh(x):
        return x
else:
    _le64toh = rarithmetic.byteswap


class Seed:
    k0l = k1l = r_uint64(0)
    initialized = False
seed = Seed()


def select_random_seed(s):
    """'s' is a string of length 16"""
    seed.k0l = (
      ord(s[0]) | ord(s[1]) << 8 | ord(s[2]) << 16 | ord(s[3]) << 24 |
      ord(s[4]) << 32 | ord(s[5]) << 40 | ord(s[6]) << 48 | ord(s[7]) << 56)
    seed.k1l = (
      ord(s[8]) | ord(s[9]) << 8 | ord(s[10]) << 16 | ord(s[11]) << 24 |
      ord(s[12]) << 32 | ord(s[13]) << 40 | ord(s[14]) << 48 | ord(s[15]) << 56)


random_ctx = rurandom.init_urandom()

def lcg_urandom(value):
    # Quite unsure what the point of this function is, given that a hash
    # seed of the form '%s\x00\x00\x00..' should be just as hard to
    # guess as this one.  We copy it anyway from CPython for the case
    # where 'value' is a 32-bit unsigned number, but if it is not, we
    # fall back to the '%s\x00\x00\x00..' form.
    if value == '0':
        value = ''
    try:
        x = r_uint(r_uint32(value))
    except (ValueError, OverflowError):
        x = r_uint(0)
    if str(x) == value:
        s = ''
        for index in range(16):
            x *= 214013
            x += 2531011
            x = r_uint(r_uint32(x))
            s += chr((x >> 16) & 0xff)
    else:
        if len(value) < 16:
            s = value + '\x00' * (16 - len(value))
        else:
            s = value[:16]
    return s

env_var_name = "PYTHONHASHSEED"

@dont_inline
def initialize_from_env():
    # This uses the same algorithms as CPython 3.5.  The environment
    # variable we read also defaults to "PYTHONHASHSEED".  If needed,
    # a different RPython interpreter can patch the value of the
    # global variable 'env_var_name', or completely patch this function
    # with a different one.
    value = os.environ.get(env_var_name)
    if len(value) > 0 and value != "random":
        s = lcg_urandom(value)
    else:
        s = rurandom.urandom(random_ctx, 16)
    select_random_seed(s)
    seed.initialized = True


@contextmanager
def choosen_seed(new_k0, new_k1, test_misaligned_path=False):
    """For tests."""
    global misaligned_is_fine
    old = seed.k0l, seed.k1l, misaligned_is_fine
    seed.k0l = _le64toh(r_uint64(new_k0))
    seed.k1l = _le64toh(r_uint64(new_k1))
    if test_misaligned_path:
        misaligned_is_fine = False
    yield
    seed.k0l, seed.k1l, misaligned_is_fine = old

def get_current_seed():
    return _le64toh(seed.k0l), _le64toh(seed.k1l)


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

    if we_are_translated() and not seed.initialized:
        initialize_from_env()
    k0 = seed.k0l
    k1 = seed.k1l
    b = r_uint64(size) << 56
    v0 = k0 ^ magic0
    v1 = k1 ^ magic1
    v2 = k0 ^ magic2
    v3 = k1 ^ magic3

    direct = (misaligned_is_fine or
                 (rffi.cast(lltype.Signed, addr_in) & 7) == 0)
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
