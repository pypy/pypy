from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.jit.backend.x86.arch import WORD


if WORD == 4:
    _instruction = "movl %%gs:0, %0"
else:
    _instruction = "movq %%fs:0, %0"

eci = ExternalCompilationInfo(post_include_bits=['''
#define RPY_STM_JIT  1
static long pypy__threadlocal_base(void)
{
    /* XXX ONLY LINUX WITH GCC/CLANG FOR NOW XXX */
    long result;
    asm("%s" : "=r"(result));
    return result;
}
''' % _instruction])


threadlocal_base = rffi.llexternal(
    'pypy__threadlocal_base',
    [], lltype.Signed,
    compilation_info=eci,
    _nowrapper=True,
    transactionsafe=True)
