from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.clibffi import FFI_DEFAULT_ABI, FFI_SYSV, FFI_VFP
from rpython.rtyper.tool import rffi_platform
from rpython.translator.platform import CompilationError

eci = ExternalCompilationInfo(
    post_include_bits=["""
// we need to disable optimizations so the compiler does not remove this
// function when checking if the file compiles
static void __attribute__((optimize("O0"))) pypy__arm_has_vfp()
{
    asm volatile("VMOV s0, s1");
}
    """])

def detect_hardfloat():
    return FFI_DEFAULT_ABI == FFI_VFP

def detect_float():
    """Check for hardware float support
    we try to compile a function containing a VFP instruction, and if the
    compiler accepts it we assume we are fine
    """
    try:
        rffi_platform.verify_eci(eci)
        return True
    except CompilationError:
        return False
