import time

from pypy.rlib.rarithmetic import r_longlong, r_ulonglong
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import rffi


def read_timestamp():
    # returns a longlong.  When running on top of python, build
    # the result a bit arbitrarily.
    return r_longlong(r_ulonglong(long(time.time() * 500000000)))


class ReadTimestampEntry(ExtRegistryEntry):
    _about_ = read_timestamp

    def compute_result_annotation(self):
        from pypy.annotation.model import SomeInteger
        return SomeInteger(knowntype=r_longlong)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.genop("ll_read_timestamp", [], resulttype=rffi.LONGLONG)
