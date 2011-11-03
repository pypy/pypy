""" Various rpython-level functions for dlopen
"""

from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import rffi
from pypy.rlib.rarithmetic import r_uint
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import platform

import sys

# maaaybe isinstance here would be better. Think
_MSVC = platform.name == "msvc"
_MINGW = platform.name == "mingw32"
_WIN32 = _MSVC or _MINGW
_MAC_OS = platform.name == "darwin"
_FREEBSD = platform.name == "freebsd"

if _WIN32:
    from pypy.rlib import rwin32
    includes = ['windows.h']
else:
    includes = ['dlfcn.h']

if _MAC_OS:
    pre_include_bits = ['#define MACOSX']
else: 
    pre_include_bits = []

if _FREEBSD or _WIN32:
    libraries = []
else:
    libraries = ['dl']

eci = ExternalCompilationInfo(
    pre_include_bits = pre_include_bits,
    includes = includes,
    libraries = libraries,
)

class CConfig:
    _compilation_info_ = eci

    RTLD_LOCAL = rffi_platform.DefinedConstantInteger('RTLD_LOCAL')
    RTLD_GLOBAL = rffi_platform.DefinedConstantInteger('RTLD_GLOBAL')
    RTLD_NOW = rffi_platform.DefinedConstantInteger('RTLD_NOW')

class cConfig:
    pass

for k, v in rffi_platform.configure(CConfig).items():
    setattr(cConfig, k, v)

def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci, **kwds)

class DLOpenError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)


if not _WIN32:
    c_dlopen = external('dlopen', [rffi.CCHARP, rffi.INT], rffi.VOIDP)
    c_dlclose = external('dlclose', [rffi.VOIDP], rffi.INT, threadsafe=False)
    c_dlerror = external('dlerror', [], rffi.CCHARP)
    c_dlsym = external('dlsym', [rffi.VOIDP, rffi.CCHARP], rffi.VOIDP)

    DLLHANDLE = rffi.VOIDP

    RTLD_LOCAL = cConfig.RTLD_LOCAL
    RTLD_GLOBAL = cConfig.RTLD_GLOBAL
    RTLD_NOW = cConfig.RTLD_NOW

    def dlerror():
        # XXX this would never work on top of ll2ctypes, because
        # ctypes are calling dlerror itself, unsure if I can do much in this
        # area (nor I would like to)
        res = c_dlerror()
        if not res:
            return ""
        return rffi.charp2str(res)

    def dlopen(name, mode=-1):
        """ Wrapper around C-level dlopen
        """
        if mode == -1:
            if RTLD_LOCAL is not None:
                mode = RTLD_LOCAL | RTLD_NOW
            else:
                mode = RTLD_NOW
        res = c_dlopen(name, rffi.cast(rffi.INT, mode))
        if not res:
            err = dlerror()
            raise DLOpenError(err)
        return res

    dlclose = c_dlclose

    def dlsym(libhandle, name):
        """ Wrapper around C-level dlsym
        """
        res = c_dlsym(libhandle, name)
        if not res:
            raise KeyError(name)
        # XXX rffi.cast here...
        return res

    def dlsym_byordinal(handle, index):
        # Never called
        raise KeyError(index)

if _WIN32:
    DLLHANDLE = rwin32.HMODULE

    def dlopen(name):
        res = rwin32.LoadLibrary(name)
        if not res:
            err = rwin32.GetLastError()
            raise DLOpenError(rwin32.FormatError(err))
        return res

    def dlclose(handle):
        res = rwin32.FreeLibrary(handle)
        if res:
            return -1
        else:
            return 0

    def dlsym(handle, name):
        res = rwin32.GetProcAddress(handle, name)
        if not res:
            raise KeyError(name)
        # XXX rffi.cast here...
        return res

    def dlsym_byordinal(handle, index):
        # equivalent to MAKEINTRESOURCEA
        intresource = rffi.cast(rffi.CCHARP, r_uint(index) & 0xFFFF)
        res = rwin32.GetProcAddress(handle, intresource)
        if not res:
            raise KeyError(index)
        # XXX rffi.cast here...
        return res
    
    LoadLibrary = rwin32.LoadLibrary
