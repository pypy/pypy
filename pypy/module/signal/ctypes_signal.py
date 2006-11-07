from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
from ctypes import *


assert 0, "not used so far =============================================="


signal_names = ['SIGINT', 'SIGTERM', 'SIGKILL',
                # ...
                ]


sighandler_t = CFUNCTYPE(None, c_int)

signal = libc.signal
signal.restype = sighandler_t
signal.argtypes = [c_int, sighandler_t]


class CConfig:
    _includes_ = ('signal.h',)

##    struct_sigaction = ctypes_platform.Struct('struct sigaction',
##                                              [('sa_handler', sighandler_t)])

for name in signal_names:
    setattr(CConfig, name, ctypes_platform.DefinedConstantInteger(name))

globals().update(ctypes_platform.configure(CConfig))


##sigaction = libc.sigaction
##sigaction.restype = c_int
##sigaction.argtypes = [c_int, POINTER(struct_sigaction),
##                      POINTER(struct_sigaction)]
