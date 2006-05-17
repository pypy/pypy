from pypy.rpython.rctypes.tool import ctypes_platform
from ctypes import *
from pypy.rpython.rctypes.tool import util      # ctypes.util from 0.9.9.6

includes = ('sys/poll.h',
            'sys/select.h',
            )
constant_names = '''POLLIN POLLPRI POLLOUT POLLERR POLLHUP POLLNVAL
    POLLRDNORM POLLRDBAND POLLWRNORM POLLWEBAND POLLMSG'''.split()

class CConfig:
    _header_ = ''.join(['#include <%s>\n' % filename for filename in includes])
    locals().update(map(lambda name: (name, ctypes_platform.DefinedConstantInteger(name)), constant_names))
    nfds_t = ctypes_platform.SimpleType('nfds_t')
    pollfd = ctypes_platform.Struct('struct pollfd',
                                    [('fd', c_int),
                                     ('events', c_short),
                                     ('revents', c_short)])
    
globals().update(ctypes_platform.configure(CConfig))
constants = {}
for name in constant_names:
    value = globals()[name]
    if value is not None:
        constants[name] = value
        
dllname = util.find_library('c')
assert dllname is not None
libc = cdll.LoadLibrary(dllname)

poll = libc.poll
poll.argtypes = [POINTER(pollfd), nfds_t, c_int]
poll.restype = c_int

strerror = libc.strerror
strerror.argtypes = [c_int]
strerror.restype = c_char_p
