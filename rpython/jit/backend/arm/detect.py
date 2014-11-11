import os

from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.tool import rffi_platform
from rpython.rlib.clibffi import FFI_DEFAULT_ABI, FFI_SYSV, FFI_VFP
from rpython.translator.platform import CompilationError
from rpython.rlib.debug import debug_print, debug_start, debug_stop

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


def detect_arch_version(filename="/proc/cpuinfo"):
    fd = os.open(filename, os.O_RDONLY, 0644)
    n = 0
    debug_start("jit-backend-arch")
    try:
        buf = os.read(fd, 2048)
        if not buf:
            n = 6  # we assume ARMv6 as base case
            debug_print("Could not detect ARM architecture "
                        "version, assuming", "ARMv%d" % n)
    finally:
        os.close(fd)
    # "Processor       : ARMv%d-compatible processor rev 7 (v6l)"
    i = buf.find('ARMv')
    if i == -1:
        n = 6
        debug_print("Could not detect architecture version, "
                    "falling back to", "ARMv%d" % n)
    else:
        n = int(buf[i + 4])

    if n < 6:
        raise ValueError("Unsupported ARM architecture version")

    debug_print("Detected", "ARMv%d" % n)

    if n > 7:
        n = 7
        debug_print("Architecture version not explicitly supported, "
                    "falling back to", "ARMv%d" % n)
    debug_stop("jit-backend-arch")
    return n
