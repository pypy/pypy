import time

import py

from pypy.rlib.rarithmetic import r_longlong
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import rffi
from pypy.tool.autopath import pypydir


eci = rffi.ExternalCompilationInfo(
    include_dirs = [str(py.path.local(pypydir).join('translator', 'c'))],
    includes=["src/timer.h"],
    separate_module_sources = [' '],
)
c_read_timestamp = rffi.llexternal(
    'pypy_read_timestamp', [], rffi.LONGLONG,
    compilation_info=eci, _nowrapper=True
)

def read_timestamp():
    return c_read_timestamp()


class ReadTimestampEntry(ExtRegistryEntry):
    _about_ = read_timestamp

    def compute_result_annotation(self):
        from pypy.annotation.model import SomeInteger
        return SomeInteger(knowntype=r_longlong)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.genop("ll_read_timestamp", [], resulttype=rffi.LONGLONG)
