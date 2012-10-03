#
# This is hopefully a temporary hack for x86 and x86-64
#

from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.rpython import annlowlevel
from pypy.jit.codewriter import longlong
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.jit.backend.x86.arch import WORD
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib import rgc
from pypy.module.thread.ll_thread import get_ident


if WORD == 4:
    _instruction = "movl %%gs:0, %0"
else:
    _instruction = "movq %%fs:0, %0"

eci = ExternalCompilationInfo(post_include_bits=['''
static long pypy__threadlocal_base(void)
{
    /* XXX ONLY LINUX WITH GCC FOR NOW XXX */
    long result;
    asm("%s" : "=r"(result));
    return result;
}
''' % _instruction])


threadlocal_base = rffi.llexternal(
    'pypy__threadlocal_base',
    [], lltype.Signed,
    compilation_info=eci)


def tl_segment_prefix(mc):
    if WORD == 4:
        mc.writechar('\x65')   # %gs:
    else:
        mc.writechar('\x64')   # %fs:

# ____________________________________________________________


FAILARGS_LIMIT = 1000     # xxx repeated constant

ASSEMBLER_THREAD_LOCAL = lltype.GcStruct(
    'ASSEMBLER_THREAD_LOCAL',
    ('fail_ebp', lltype.Signed),
    ('fail_boxes_count', lltype.Signed),
    ('fail_boxes_ptr', lltype.FixedSizeArray(llmemory.GCREF, FAILARGS_LIMIT)),
    ('fail_boxes_int', lltype.FixedSizeArray(lltype.Signed, FAILARGS_LIMIT)),
    ('fail_boxes_float', lltype.FixedSizeArray(longlong.FLOATSTORAGE,
                                               FAILARGS_LIMIT)),
    )

@rgc.no_collect
def get_asm_tlocal(cpu):
    id = get_ident()
    return cpu.assembler.asmtlocals[id]

def prepare_asm_tlocal(cpu):
    id = get_ident()
    if id not in cpu.assembler.asmtlocals:
        cpu.assembler.asmtlocals[id] = lltype.malloc(ASSEMBLER_THREAD_LOCAL)

def fail_boxes_int_addr(tlocal, num):
    tgt = llmemory.cast_ptr_to_adr(tlocal)
    tgt += rffi.offsetof(ASSEMBLER_THREAD_LOCAL, 'fail_boxes_int')
    tgt += num * rffi.sizeof(lltype.Signed)
    return rffi.cast(lltype.Signed, tgt)

def fail_boxes_ptr_addr(tlocal, num):
    tgt = llmemory.cast_ptr_to_adr(tlocal)
    tgt += rffi.offsetof(ASSEMBLER_THREAD_LOCAL, 'fail_boxes_ptr')
    tgt = rffi.cast(lltype.Signed, tgt)
    tgt += num * rffi.sizeof(llmemory.GCREF)
    return tgt

def fail_boxes_float_addr(tlocal, num):
    tgt = llmemory.cast_ptr_to_adr(tlocal)
    tgt += rffi.offsetof(ASSEMBLER_THREAD_LOCAL, 'fail_boxes_float')
    tgt += num * rffi.sizeof(longlong.FLOATSTORAGE)
    return rffi.cast(lltype.Signed, tgt)
