"""
Support for 'long long' on 32-bits: this is done by casting all floats
to long longs, and using long longs systematically.

On 64-bit platforms, we use float directly to avoid the cost of
converting them back and forth.
"""

import sys
from pypy.rpython.lltypesystem import lltype


if sys.maxint > 2147483647:
    # ---------- 64-bit platform ----------
    # the type FloatStorage is just a float

    from pypy.rlib.objectmodel import compute_hash

    is_64_bit = True
    supports_longlong = False
    r_float_storage = float
    FLOATSTORAGE = lltype.Float

    getfloatstorage = lambda x: x
    getrealfloat    = lambda x: x
    gethash         = compute_hash
    is_longlong     = lambda TYPE: False

    # -------------------------------------
else:
    # ---------- 32-bit platform ----------
    # the type FloatStorage is r_longlong, and conversion is needed

    from pypy.rlib import rarithmetic, longlong2float

    is_64_bit = False
    supports_longlong = True
    r_float_storage = rarithmetic.r_longlong
    FLOATSTORAGE = lltype.SignedLongLong

    getfloatstorage = longlong2float.float2longlong
    getrealfloat    = longlong2float.longlong2float
    gethash         = lambda xll: rarithmetic.intmask(xll - (xll >> 32))
    is_longlong     = lambda TYPE: (TYPE == lltype.SignedLongLong or
                                    TYPE == lltype.UnsignedLongLong)

    # -------------------------------------

ZEROF = getfloatstorage(0.0)
