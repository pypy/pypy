""" Meta-data for the low-level types """
import os

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.objectmodel import specialize

class TypeSpec(object):
    def __init__(self, name, T):
        self.name = name
        self.T = T

    def _freeze_(self):
        return True

bool_spec = TypeSpec("bool", lltype.Bool)
int8_spec = TypeSpec("int8", rffi.SIGNEDCHAR)
uint8_spec = TypeSpec("uint8", rffi.UCHAR)
int16_spec = TypeSpec("int16", rffi.SHORT)
uint16_spec = TypeSpec("uint16", rffi.USHORT)
int32_spec = TypeSpec("int32", rffi.INT)
uint32_spec = TypeSpec("uint32", rffi.UINT)
long_spec = TypeSpec("long", rffi.LONG)
ulong_spec = TypeSpec("ulong", rffi.ULONG)
int64_spec = TypeSpec("int64", rffi.LONGLONG)
uint64_spec = TypeSpec("uint64", rffi.ULONGLONG)

float32_spec = TypeSpec("float32", rffi.FLOAT)
float64_spec = TypeSpec("float64", rffi.DOUBLE)
float16_spec = TypeSpec("float16", rffi.SHORT)

ENABLED_LONG_DOUBLE = False
long_double_size = rffi.sizeof_c_type('long double', ignore_errors=True)
if long_double_size == 8 and os.name == 'nt':
    # this is a lie, or maybe a wish, MS fakes longdouble math with double
    long_double_size = 12


