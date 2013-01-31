from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.jit.backend.x86.arch import WORD


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
