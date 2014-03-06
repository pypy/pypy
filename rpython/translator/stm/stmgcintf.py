import os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.conftest import cdir as cdir2


cdir = os.path.abspath(os.path.join(cdir2, '..', 'stm'))

separate_source = '''
//#define _GC_DEBUG   2       /* XXX move elsewhere */

#include "src_stm/stmgc.h"

extern Signed pypy_stmcb_size(void*);
extern void pypy_stmcb_trace(void*, void(*)(void*));

inline size_t stmcb_size(struct object_s *obj) {
    return pypy_stmcb_size(obj);
}

inline void stmcb_trace(struct object_s *obj, void visit(object_t **)) {
    pypy_stmcb_trace(obj, (void(*)(void*))visit);
}

#include "src_stm/stmgc.c"
'''

eci = ExternalCompilationInfo(
    include_dirs = [cdir, cdir2],
    includes = ['src_stm/stmgc.h'],
    pre_include_bits = ['#define RPY_STM 1'],
    separate_module_sources = [separate_source],
)

GCPTR = lltype.Ptr(rffi.COpaque('rpyobj_t',
                                hints={"is_stm_header": True}))
CALLBACK_TX = lltype.Ptr(lltype.FuncType([GCPTR, rffi.INT_real],
                                         rffi.INT_real))
