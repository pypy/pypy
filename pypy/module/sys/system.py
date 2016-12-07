"""Information about the current system."""
import sys
import os

from pypy.objspace.std.complexobject import HASH_IMAG
from pypy.objspace.std.floatobject import HASH_INF, HASH_NAN
from pypy.objspace.std.intobject import HASH_MODULUS
from pypy.objspace.std.bytesobject import HASH_ALGORITHM
from pypy.interpreter import gateway
from rpython.rlib import rbigint, rfloat
from rpython.rtyper.lltypesystem import lltype, rffi

PLATFORM = 'linux' if sys.platform.startswith('linux') else sys.platform

app = gateway.applevel("""
"NOT_RPYTHON"
from _structseq import structseqtype, structseqfield
class float_info(metaclass=structseqtype):

    max = structseqfield(0)
    max_exp = structseqfield(1)
    max_10_exp = structseqfield(2)
    min = structseqfield(3)
    min_exp = structseqfield(4)
    min_10_exp = structseqfield(5)
    dig = structseqfield(6)
    mant_dig = structseqfield(7)
    epsilon = structseqfield(8)
    radix = structseqfield(9)
    rounds = structseqfield(10)

class int_info(metaclass=structseqtype):
    bits_per_digit = structseqfield(0)
    sizeof_digit = structseqfield(1)

class hash_info(metaclass=structseqtype):
    width = structseqfield(0)
    modulus = structseqfield(1)
    inf = structseqfield(2)
    nan = structseqfield(3)
    imag = structseqfield(4)
    algorithm = structseqfield(5)
    hash_bits = structseqfield(6)
    seed_bits = structseqfield(7)
    cutoff = structseqfield(8)

class thread_info(metaclass=structseqtype):
    name = structseqfield(0)
    lock = structseqfield(1)
    version = structseqfield(2)
""")


def get_float_info(space):
    info_w = [
        space.wrap(rfloat.DBL_MAX),
        space.wrap(rfloat.DBL_MAX_EXP),
        space.wrap(rfloat.DBL_MAX_10_EXP),
        space.wrap(rfloat.DBL_MIN),
        space.wrap(rfloat.DBL_MIN_EXP),
        space.wrap(rfloat.DBL_MIN_10_EXP),
        space.wrap(rfloat.DBL_DIG),
        space.wrap(rfloat.DBL_MANT_DIG),
        space.wrap(rfloat.DBL_EPSILON),
        space.wrap(rfloat.FLT_RADIX),
        space.wrap(rfloat.FLT_ROUNDS),
    ]
    w_float_info = app.wget(space, "float_info")
    return space.call_function(w_float_info, space.newtuple(info_w))

def get_int_info(space):
    bits_per_digit = rbigint.SHIFT
    sizeof_digit = rffi.sizeof(rbigint.STORE_TYPE)
    info_w = [
        space.wrap(bits_per_digit),
        space.wrap(sizeof_digit),
    ]
    w_int_info = app.wget(space, "int_info")
    return space.call_function(w_int_info, space.newtuple(info_w))

def get_hash_info(space):
    HASH_HASH_BITS = 8 * rffi.sizeof(lltype.Signed)
    HASH_SEED_BITS = 0    # XXX don't know what this is supposed to be
    HASH_CUTOFF = 0
    info_w = [
        space.wrap(8 * rffi.sizeof(lltype.Signed)),
        space.wrap(HASH_MODULUS),
        space.wrap(HASH_INF),
        space.wrap(HASH_NAN),
        space.wrap(HASH_IMAG),
        space.wrap(HASH_ALGORITHM),
        space.wrap(HASH_HASH_BITS),
        space.wrap(HASH_SEED_BITS),
        space.wrap(HASH_CUTOFF),
    ]
    w_hash_info = app.wget(space, "hash_info")
    return space.call_function(w_hash_info, space.newtuple(info_w))

def get_float_repr_style(space):
    return space.wrap("short")

def get_thread_info(space):
    if not space.config.objspace.usemodules.thread:
        return None
    from rpython.rlib import rthread
    if rthread.RPYTHREAD_NAME == "pthread":
        w_lock = space.wrap("semaphore" if rthread.USE_SEMAPHORES
                            else "mutex+cond")
        if rthread.CS_GNU_LIBPTHREAD_VERSION is not None:
            w_version = space.wrap(
                os.confstr(rthread.CS_GNU_LIBPTHREAD_VERSION))
        else:
            w_version = space.w_None
    else:
        w_lock = space.w_None
        w_version = space.w_None
    info_w = [
        space.wrap(rthread.RPYTHREAD_NAME),
        w_lock, w_version,
    ]
    w_thread_info = app.wget(space, "thread_info")
    return space.call_function(w_thread_info, space.newtuple(info_w))

def getdlopenflags(space):
    return space.wrap(space.sys.dlopenflags)

def setdlopenflags(space, w_flags):
    space.sys.dlopenflags = space.int_w(w_flags)
