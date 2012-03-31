import py
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo


cdir = py.path.local(pypydir) / 'translator' / 'stm'
cdir2 = py.path.local(pypydir) / 'translator' / 'c'

eci = ExternalCompilationInfo(
    include_dirs = [cdir, cdir2],
    post_include_bits = ['''
#include "src_stm/atomic_ops.h"
#define pypy_bool_cas(ptr, old, _new)                \\
           bool_cas((volatile unsigned long*)(ptr),  \\
                    (unsigned long)(old),            \\
                    (unsigned long)(_new))
'''],
)


bool_cas = rffi.llexternal('pypy_bool_cas', [llmemory.Address]*3, lltype.Bool,
                           compilation_info=eci, macro=True)
