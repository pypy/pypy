"""
Processor auto-detection
"""
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
            return 'x86'
        # assume we have 'uname'
        mach = os.popen('uname -m', 'r').read().strip()
        if not mach:
            raise ProcessorAutodetectError, "cannot run 'uname -m'"
    try:
        return {'i386': 'x86',
                'i486': 'x86',
                'i586': 'x86',
                'i686': 'x86',
                'i86pc': 'x86',    # Solaris/Intel
                'x86':   'x86',    # Apple
                'Power Macintosh': 'ppc',
                'x86_64': 'x86',
                'amd64': 'x86',    # freebsd
                'AMD64': 'x86',    # win64
                'armv7l': 'arm',
                }[mach]
    except KeyError:
        return mach

def autodetect_main_model_and_size():
    model = autodetect_main_model()
    if sys.maxint == 2**31-1:
        model += '_32'
    elif sys.maxint == 2**63-1:
        model += '_64'
    else:
        raise AssertionError, "bad value for sys.maxint"
    return model

def autodetect():
    model = autodetect_main_model()
    if sys.maxint == 2**63-1:
        model += '_64'
    else:
        assert sys.maxint == 2**31-1
        if model == 'x86':
            from rpython.jit.backend.x86.detect_sse2 import detect_sse2
            if not detect_sse2():
                model = 'x86-without-sse2'
    if model == 'arm':
            from rpython.jit.backend.arm.detect import detect_hardfloat, detect_float
            if detect_hardfloat():
                model = 'armhf'
            assert detect_float(), 'the JIT-compiler requires a vfp unit'
    return model
    
def getcpuclassname(backend_name="auto"):
    if backend_name == "auto":
        backend_name = autodetect()
    if backend_name == 'x86':
        return "rpython.jit.backend.x86.runner", "CPU"
    elif backend_name == 'x86-without-sse2':
        return "rpython.jit.backend.x86.runner", "CPU386_NO_SSE2"
    elif backend_name == 'x86_64':
        return "rpython.jit.backend.x86.runner", "CPU_X86_64"
    elif backend_name == 'cli':
        return "rpython.jit.backend.cli.runner", "CliCPU"
    elif backend_name == 'arm':
        return "rpython.jit.backend.arm.runner", "CPU_ARM"
    elif backend_name == 'armhf':
        return "rpython.jit.backend.arm.runner", "CPU_ARMHF"
    else:
        raise ProcessorAutodetectError, (
            "we have no JIT backend for this cpu: '%s'" % backend_name)

def getcpuclass(backend_name="auto"):
    modname, clsname = getcpuclassname(backend_name)
    mod = __import__(modname, {}, {}, clsname)
    return getattr(mod, clsname)

if __name__ == '__main__':
    print autodetect()
    print getcpuclassname()
