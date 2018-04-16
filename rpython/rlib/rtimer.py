import time

from rpython.rlib.rarithmetic import r_longlong, r_uint
from rpython.rlib.rarithmetic import intmask, longlongmask
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.lltypesystem import lltype, rffi

_is_64_bit = r_uint.BITS > 32

# unit of values returned by read_timestamp. Should be in sync with the ones
# defined in translator/c/debug_print.h
UNIT_TSC = 0
UNIT_NS = 1 # nanoseconds
UNIT_QUERY_PERFORMANCE_COUNTER = 2
UNITS = ('tsc', 'ns', 'QueryPerformanceCounter')

def read_timestamp():
    # Returns a longlong on 32-bit, and a regular int on 64-bit.
    # When running on top of python, build the result a bit arbitrarily.
    x = long(time.time() * 500000000)
    if _is_64_bit:
        return intmask(x)
    else:
        return longlongmask(x)

def get_timestamp_unit():
    # an unit which is as arbitrary as the way we build the result of
    # read_timestamp :)
    return UNIT_NS


class ReadTimestampEntry(ExtRegistryEntry):
    _about_ = read_timestamp

    def compute_result_annotation(self):
        from rpython.annotator.model import SomeInteger
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


class ReadTimestampEntry(ExtRegistryEntry):
    _about_ = get_timestamp_unit

    def compute_result_annotation(self):
        from rpython.annotator.model import SomeInteger
        return SomeInteger(nonneg=True)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.genop("ll_get_timestamp_unit", [], resulttype=lltype.Signed)
