import py
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo


cdir = py.path.local(__file__).join('..', '..', 'translator', 'stm')
cdir2 = py.path.local(__file__).join('..', '..', 'translator', 'c')

eci = ExternalCompilationInfo(
    include_dirs = [cdir, cdir2],
    post_include_bits = ['''
#include "src_stm/atomic_ops.h"
#define pypy_bool_cas(ptr, old, _new)                \\
           bool_cas((volatile unsigned long*)(ptr),  \\
                    (unsigned long)(old),            \\
                    (unsigned long)(_new))
#define pypy_fetch_and_add(ptr, value)                    \\
           fetch_and_add((volatile unsigned long*)(ptr),  \\
                         (unsigned long)(value))
'''],
)


bool_cas = rffi.llexternal('pypy_bool_cas', [llmemory.Address]*3, lltype.Bool,
                           compilation_info=eci, macro=True, _nowrapper=True)
fetch_and_add = rffi.llexternal('pypy_fetch_and_add', [llmemory.Address,
                                                       lltype.Signed],
                                lltype.Signed, compilation_info=eci,
                                macro=True, _nowrapper=True)
