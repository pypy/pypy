"""
Processor auto-detection
"""
import sys, os


class ProcessorAutodetectError(Exception):
    pass

def autodetect():
    platform = sys.platform.lower()
    if platform.startswith('win'):   # assume an Intel Windows
        return 'i386'
    # assume we have 'uname'
    mach = os.popen('uname -m', 'r').read().strip()
    if not mach:
        raise ProcessorAutodetectError, "cannot run 'uname -m'"
    try:
        return {'i386': 'i386',
                'i486': 'i386',
                'i586': 'i386',
                'i686': 'i386',
                'i86pc': 'i386',    # Solaris/Intel
                'x86':   'i386',    # Apple
                }[mach]
    except KeyError:
        raise ProcessorAutodetectError, "unsupported processor '%s'" % mach
