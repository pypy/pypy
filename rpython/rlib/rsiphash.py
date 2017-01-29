"""
This module implements siphash-2-4, the hashing algorithm for strings
and unicodes.  You can use it explicitly by calling siphash24() with
a byte string, or you can use enable_siphash24() to enable the use
of siphash-2-4 on all RPython strings and unicodes in your program
after translation.
"""
import sys, os
from contextlib import contextmanager
from rpython.rlib import rarithmetic, rurandom
from rpython.rlib.objectmodel import not_rpython, always_inline
from rpython.rlib.objectmodel import we_are_translated, dont_inline
from rpython.rlib import rgc, jit
from rpython.rlib.rarithmetic import r_uint64, r_uint32, r_uint
from rpython.rlib.rawstorage import misaligned_is_fine
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi, rstr
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.extregistry import ExtRegistryEntry


if sys.byteorder == 'little':
    def _le64toh(x):
        return x
else:
    _le64toh = rarithmetic.byteswap


class Seed:
    k0l = k1l = r_uint64(0)
seed = Seed()


def _decode64(s):
    return (r_uint64(ord(s[0])) |
            r_uint64(ord(s[1])) << 8 |
            r_uint64(ord(s[2])) << 16 |
            r_uint64(ord(s[3])) << 24 |
            r_uint64(ord(s[4])) << 32 |
            r_uint64(ord(s[5])) << 40 |
            r_uint64(ord(s[6])) << 48 |
            r_uint64(ord(s[7])) << 56)

def select_random_seed(s):
    """'s' is a string of length 16"""
    seed.k0l = _decode64(s)
    seed.k1l = _decode64(s[8:16])


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

def initialize_from_env():
    # This uses the same algorithms as CPython 3.5.  The environment
    # variable we read also defaults to "PYTHONHASHSEED".  If needed,
    # a different RPython interpreter can patch the value of the
    # global variable 'env_var_name', or just pass a different init
    # function to enable_siphash24().
    value = os.environ.get(env_var_name)
    if len(value) > 0 and value != "random":
        s = lcg_urandom(value)
    else:
        s = rurandom.urandom(random_ctx, 16)
    select_random_seed(s)

_FUNC = lltype.Ptr(lltype.FuncType([], lltype.Void))

def enable_siphash24(*init):
    """
    Enable the use of siphash-2-4 for all RPython strings and unicodes
    in the translated program.  You must call this function anywhere
    from your interpreter (from a place that is annotated).  Optionally,
    you can pass a function to call to initialize the state; the default
    is 'initialize_from_env' above.  Don't call this more than once.
    """
    _internal_enable_siphash24()
    if init:
        (init_func,) = init
    else:
        init_func = initialize_from_env
    llop.call_at_startup(lltype.Void, llexternal(_FUNC, init_func))

def _internal_enable_siphash24():
    pass

class Entry(ExtRegistryEntry):
    _about_ = _internal_enable_siphash24

    def compute_result_annotation(self):
        translator = self.bookkeeper.annotator.translator
        if hasattr(translator, 'll_hash_string'):
            assert translator.ll_hash_string == ll_hash_string_siphash24
        else:
            translator.ll_hash_string = ll_hash_string_siphash24

    def specialize_call(self, hop):
        hop.exception_cannot_occur()

@rgc.no_collect
def ll_hash_string_siphash24(ll_s):
    """Called indirectly from lltypesystem/rstr.py, by redirection from
    objectmodel.ll_string_hash().
    """
    from rpython.rlib.rarithmetic import intmask

    # This function is entirely @rgc.no_collect.
    length = len(ll_s.chars)
    if lltype.typeOf(ll_s).TO.chars.OF == lltype.Char:   # regular STR
        addr = rstr._get_raw_buf_string(rstr.STR, ll_s, 0)
    else:
        # NOTE: a latin-1 unicode string must have the same hash as the
        # corresponding byte string.  If the unicode is all within
        # 0-255, then we need to allocate a byte buffer and copy the
        # latin-1 encoding in it manually.
        for i in range(length):
            if ord(ll_s.chars[i]) > 0xFF:
                addr = rstr._get_raw_buf_unicode(rstr.UNICODE, ll_s, 0)
                length *= rffi.sizeof(rstr.UNICODE.chars.OF)
                break
        else:
            p = lltype.malloc(rffi.CCHARP.TO, length, flavor='raw')
            i = 0
            while i < length:
                p[i] = chr(ord(ll_s.chars[i]))
                i += 1
            x = _siphash24(llmemory.cast_ptr_to_adr(p), length)
            lltype.free(p, flavor='raw')
            return intmask(x)
    x = _siphash24(addr, length)
    keepalive_until_here(ll_s)
    return intmask(x)


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


@rgc.no_collect
def _siphash24(addr_in, size):
    """Takes an address pointer and a size.  Returns the hash as a r_uint64,
    which can then be casted to the expected type."""

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


@jit.dont_look_inside
def siphash24(s):
    """'s' is a normal string.  Returns its siphash-2-4 as a r_uint64.
    Don't forget to cast the result to a regular integer if needed,
    e.g. with rarithmetic.intmask().
    """
    with rffi.scoped_nonmovingbuffer(s) as p:
        return _siphash24(llmemory.cast_ptr_to_adr(p), len(s))
