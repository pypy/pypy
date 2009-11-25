"""
Processor auto-detection
"""
import autopath
import sys, os


class ProcessorAutodetectError(Exception):
    pass

def autodetect_main_model():
    mach = None
    try:
        import platform
        mach = platform.machine()
    except ImportError:
        pass
    if not mach:
        platform = sys.platform.lower()
        if platform.startswith('win'):   # assume an Intel Windows
            return 'i386'
        # assume we have 'uname'
        mach = os.popen('uname -m', 'r').read().strip()
        if not mach:
            raise ProcessorAutodetectError, "cannot run 'uname -m'"
    if mach == 'x86_64':
        if sys.maxint == 2147483647:
            mach = 'x86'     # it's a 64-bit processor but in 32-bits mode, maybe
        else:
            assert sys.maxint == 2 ** 63 - 1
    try:
        return {'i386': 'i386',
                'i486': 'i386',
                'i586': 'i386',
                'i686': 'i386',
                'i86pc': 'i386',    # Solaris/Intel
                'x86':   'i386',    # Apple
                'Power Macintosh': 'ppc',
                'x86_64': 'x86_64', 
                }[mach]
    except KeyError:
        raise ProcessorAutodetectError, "unsupported processor '%s'" % mach

def autodetect():
    model = autodetect_main_model()
    if model in ('i386', 'x86'):
        from pypy.jit.backend.x86.detect_sse2 import detect_sse2
        if not detect_sse2():
            model = 'x86-without-sse2'
    return model

def getcpuclass(backend_name="auto"):
    if backend_name == "auto":
        backend_name = autodetect()
    if backend_name in ('i386', 'x86'):
        from pypy.jit.backend.x86.runner import CPU
    elif backend_name == 'x86-without-sse2':
        from pypy.jit.backend.x86.runner import CPU386_NO_SSE2 as CPU
    elif backend_name == 'cli':
        from pypy.jit.backend.cli.runner import CliCPU as CPU
    elif backend_name == 'llvm':
        from pypy.jit.backend.llvm.runner import LLVMCPU as CPU
    else:
        raise ProcessorAutodetectError, "unsupported cpu '%s'" % backend_name
    return CPU

if __name__ == '__main__':
    print autodetect()
