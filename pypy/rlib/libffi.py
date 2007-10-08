
""" Various rpython-level functions for dlopen and libffi wrapping
"""

from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import lltype, rffi

includes = ['dlfcn.h']

class CConfig:
    RTLD_LOCAL = rffi_platform.DefinedConstantInteger('RTLD_LOCAL')
    RTLD_NOW = rffi_platform.DefinedConstantInteger('RTLD_NOW')
    _includes_ = includes

class cConfig:
    pass

cConfig.__dict__.update(rffi_platform.configure(CConfig))

def external(name, args, result):
    return rffi.llexternal(name, args, result, includes=includes,
                           libraries=['dl'])

c_dlopen = external('dlopen', [rffi.CCHARP, rffi.INT], rffi.VOIDP)
c_dlclose = external('dlclose', [rffi.VOIDP], rffi.INT)
c_dlerror = external('dlerror', [], rffi.CCHARP)
c_dlsym = external('dlsym', [rffi.VOIDP, rffi.CCHARP], rffi.VOIDP)

RTLD_LOCAL = cConfig.RTLD_LOCAL
RTLD_NOW = cConfig.RTLD_NOW

def dlerror():
    # XXX this would never work on top of ll2ctypes, because
    # ctypes are calling dlerror itself, unsure if I can do much in this
    # area (nor I would like to)
    res = c_dlerror()
    if not res:
        return ""
    return rffi.charp2str(res)

def dlopen(name):
    """ Wrapper around C-level dlopen
    """
    if RTLD_LOCAL is not None:
        mode = RTLD_LOCAL | RTLD_NOW
    else:
        mode = RTLD_NOW
    res = c_dlopen(name, mode)
    if not res:
        raise OSError(dlerror())
    return res

def dlsym(libhandle, name):
    """ Wrapper around C-level dlsym
    """
    res = c_dlsym(libhandle, name)
    if not res:
        raise KeyError(name)
    # XXX rffi.cast here...
    return res

class CDLL:
    def __init__(self, libname):
        self.lib = dlopen(libname)

    def __del__(self):
        c_dlclose(self.lib)

    def getpointer(self, name):
        return dlsym(self.lib, name)
