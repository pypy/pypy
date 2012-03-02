import time

from pypy.rlib.rarithmetic import r_longlong, r_ulonglong, r_uint
from pypy.rlib.rarithmetic import intmask, longlongmask
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype, rffi

_is_64_bit = r_uint.BITS > 32


def read_timestamp():
    # Returns a longlong on 32-bit, and a regular int on 64-bit.
    # When running on top of python, build the result a bit arbitrarily.
    x = long(time.time() * 500000000)
    if _is_64_bit:
        return intmask(x)
    else:
        return longlongmask(x)


class ReadTimestampEntry(ExtRegistryEntry):
    _about_ = read_timestamp

    def compute_result_annotation(self):
        from pypy.annotation.model import SomeInteger
        if _is_64_bit:
            return SomeInteger()
        else:
            return SomeInteger(knowntype=r_longlong)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        if _is_64_bit:
            resulttype = lltype.Signed
        else:
            resulttype = rffi.LONGLONG
        return hop.genop("ll_read_timestamp", [], resulttype=resulttype)
