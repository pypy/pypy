"""
Processor auto-detection
"""
import sys, os
from rpython.rtyper.tool.rffi_platform import getdefined
from rpython.translator.platform import is_host_build


class ProcessorAutodetectError(Exception):
    pass


def detect_main_model_and_size_from_platform():
    # based on http://sourceforge.net/p/predef/wiki/Architectures/
    mapping = {
            ('x86', '64'): [
                '__amd64__', '__amd64', '__x86_64__', '__x86_64',  # AMD64
                '__ia64__', '_IA64', '__IA64__'                    # Intel Itanium (IA-64)
                ],
            ('arm', '32'): ['__arm__', '__thumb__'],
            ('x86', '32'): ['i386', '__i386', '__i386__', '__i686__',],
            ('ppc', '64'): ['__powerpc64__'],
    }
    for k, v in mapping.iteritems():
        for macro in v:
            if not getdefined(macro, ''):
                continue
            return '_'.join(k)
    raise ProcessorAutodetectError, "Cannot detect processor using compiler macros"


def detect_main_model_from_platform():
    return detect_main_model_and_size_from_platform()[0]


def autodetect_main_model():
    if not is_host_build():
        return detect_main_model_from_platform()
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
                'armv6l': 'arm',
                }[mach]
    except KeyError:
        return mach

def autodetect_main_model_and_size():
    if not is_host_build():
        return detect_main_model_and_size_from_platform()
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
    if model.startswith('arm'):
        from rpython.jit.backend.arm.detect import detect_hardfloat, detect_float
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
    elif backend_name.startswith('arm'):
        return "rpython.jit.backend.arm.runner", "CPU_ARM"
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
