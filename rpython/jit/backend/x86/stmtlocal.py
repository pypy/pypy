from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.jit.backend.x86.arch import WORD


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
    compilation_info=eci,
    threadsafe=False,
    transactionsafe=True)


def tl_segment_prefix(mc):
    if WORD == 4:
        mc.writechar('\x65')   # %gs:
    else:
        mc.writechar('\x64')   # %fs:


# special STM functions called directly by the JIT backend
stm_should_break_transaction_fn = rffi.llexternal(
    'stm_should_break_transaction',
    [], lltype.Bool,
    sandboxsafe=True, _nowrapper=True, transactionsafe=True)
stm_transaction_break_fn = rffi.llexternal(
    'stm_transaction_break',
    [llmemory.Address, llmemory.Address], lltype.Void,
    sandboxsafe=True, _nowrapper=True, transactionsafe=True)
stm_invalidate_jmp_buf_fn = rffi.llexternal(
    'stm_invalidate_jmp_buf',
    [llmemory.Address], lltype.Void,
    sandboxsafe=True, _nowrapper=True, transactionsafe=True)
stm_pointer_equal_fn = rffi.llexternal(
    'stm_pointer_equal',
    [llmemory.Address, llmemory.Address], lltype.Bool,
    sandboxsafe=True, _nowrapper=True, transactionsafe=True)


