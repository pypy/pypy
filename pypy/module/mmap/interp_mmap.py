from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
import pypy.rpython.rctypes.implementation # this defines rctypes magic
from pypy.rpython.rctypes.aerrno import geterrno
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from ctypes import *
import sys
import os
import platform

_POSIX = os.name == "posix"
_MS_WINDOWS = os.name == "nt"
_FREEBSD = "freebsd" in sys.platform
_64BIT = "64bit" in platform.architecture()[0]

class CConfig:
    _header_ = """
    #include <sys/mman.h>
    """

# constants, look in sys/mman.h and platform docs for the meaning
# some constants are linux only so they will be correctly exposed outside 
# depending on the OS
constants = {}
constant_names = ['MAP_SHARED', 'MAP_PRIVATE', 'MAP_ANON', 'MAP_ANONYMOUS',
    'PROT_READ', 'PROT_WRITE', 'PROT_EXEC', 'MAP_DENYWRITE', 'MAP_EXECUTABLE']
for name in constant_names:
    setattr(CConfig, name, ctypes_platform.DefinedConstantInteger(name))

class cConfig:
    pass

cConfig.__dict__.update(ctypes_platform.configure(CConfig))

# needed to export the constants inside and outside. see __init__.py
for name in constant_names:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value

# MAP_ANONYMOUS is not always present but it's always available at CPython level
if cConfig.MAP_ANONYMOUS is None:
    cConfig.MAP_ANONYMOUS = cConfig.MAP_ANON
    constants["MAP_ANONYMOUS"] = cConfig.MAP_ANON

locals().update(constants)

_MS_SYNC = ctypes_platform.DefinedConstantInteger("MS_SYNC")
_ACCESS_DEFAULT = 0

if _POSIX:
    def _get_page_size():
        return libc.getpagesize()

    def _get_error_msg():
        errno = geterrno()
        return libc.strerror(errno)   
