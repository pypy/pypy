import time

import py

from pypy.rlib.rarithmetic import r_longlong
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