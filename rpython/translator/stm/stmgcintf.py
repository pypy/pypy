import os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.conftest import cdir as cdir2


cdir = os.path.abspath(os.path.join(cdir2, '..', 'stm'))

_f = open(os.path.join(cdir, 'src_stm', 'stmgcintf.c'), 'r')
separate_source = _f.read()
_f.close()

eci = ExternalCompilationInfo(
    include_dirs = [cdir, cdir2],
    includes = ['src_stm/stmgcintf.h'],
    pre_include_bits = ['#define RPY_STM 1'],
    separate_module_sources = [separate_source],
)

GCPTR = lltype.Ptr(rffi.COpaque('rpyobj_t',
                                hints={"is_stm_header": True}))
CALLBACK_TX = lltype.Ptr(lltype.FuncType([GCPTR, rffi.INT_real],
                                         rffi.INT_real))
