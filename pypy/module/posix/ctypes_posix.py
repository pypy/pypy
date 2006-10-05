from pypy.rpython.rctypes.tool import ctypes_platform
from ctypes import *
from pypy.rpython.rctypes.tool import util      # ctypes.util from 0.9.9.6

from pypy.rpython.rctypes.aerrno import geterrno

includes = ['unistd.h', 'sys/types.h']

dllname = util.find_library('c')
assert dllname is not None
libc = cdll.LoadLibrary(dllname)

HAVE_UNAME = hasattr(libc, 'uname')

if HAVE_UNAME:
    includes.append('sys/utsname.h')

class CConfig:
    _header_ = ''.join(['#include <%s>\n' % filename for filename in includes])
    uid_t = ctypes_platform.SimpleType('uid_t')
    if HAVE_UNAME:
        utsname_t = ctypes_platform.Struct('struct utsname',
                                           [('sysname', c_char * 0),
                                            ('nodename', c_char * 0),
                                            ('release',c_char * 0),
                                            ('version',c_char * 0),
                                            ('machine', c_char *0),])

globals().update(ctypes_platform.configure(CConfig))

getuid = libc.getuid
getuid.argtype = []
getuid.restype = uid_t

geteuid = libc.geteuid
geteuid.argtype = []
geteuid.restype = uid_t

if HAVE_UNAME:
    libc.uname.argtype = [POINTER(utsname_t)]
    libc.uname.restype = c_int
    def uname():
        result = utsname_t()
        retC = libc.uname(pointer(result))
        if retC == -1:
            raise OSError(geterrno())
        return [result.sysname,
                result.nodename,
                result.release,
                result.version,
                result.machine,]
