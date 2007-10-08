
""" Various rpython-level functions for dlopen and libffi wrapping
"""

from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import lltype, rffi

includes = ['dlfcn.h', 'ffi.h']

FFI_TYPE_P = lltype.Ptr(lltype.ForwardReference())
FFI_TYPE_PP = rffi.CArrayPtr(FFI_TYPE_P)

class CConfig:
    _includes_ = includes

    RTLD_LOCAL = rffi_platform.DefinedConstantInteger('RTLD_LOCAL')
    RTLD_NOW = rffi_platform.DefinedConstantInteger('RTLD_NOW')

    FFI_OK = rffi_platform.ConstantInteger('FFI_OK')
    FFI_BAD_TYPEDEF = rffi_platform.ConstantInteger('FFI_BAD_TYPEDEF')
    FFI_DEFAULT_ABI = rffi_platform.ConstantInteger('FFI_DEFAULT_ABI')

    size_t = rffi_platform.SimpleType("size_t", rffi.ULONG)

    ffi_type = rffi_platform.Struct('ffi_type', [('size', rffi.ULONG),
                                                 ('alignment', rffi.USHORT),
                                                 ('type', rffi.USHORT),
                                                 ('elements', FFI_TYPE_PP)])
    # XXX elements goes here, for structures

class cConfig:
    pass

cConfig.__dict__.update(rffi_platform.configure(CConfig))

FFI_TYPE_P.TO.become(cConfig.ffi_type)
size_t = cConfig.size_t

def external(name, args, result):
    return rffi.llexternal(name, args, result, includes=includes,
                           libraries=['dl', 'ffi'])

c_dlopen = external('dlopen', [rffi.CCHARP, rffi.INT], rffi.VOIDP)
c_dlclose = external('dlclose', [rffi.VOIDP], rffi.INT)
c_dlerror = external('dlerror', [], rffi.CCHARP)
c_dlsym = external('dlsym', [rffi.VOIDP, rffi.CCHARP], rffi.VOIDP)

RTLD_LOCAL = cConfig.RTLD_LOCAL
RTLD_NOW = cConfig.RTLD_NOW
FFI_OK = cConfig.FFI_OK
FFI_BAD_TYPEDEF = cConfig.FFI_BAD_TYPEDEF
FFI_DEFAULT_ABI = cConfig.FFI_DEFAULT_ABI
FFI_CIFP = rffi.COpaquePtr('ffi_cif', includes=includes)

c_ffi_prep_cif = external('ffi_prep_cif', [FFI_CIFP, rffi.USHORT, rffi.UINT,
                                           FFI_TYPE_P, FFI_TYPE_PP], rffi.INT)
c_ffi_call = external('ffi_call', [FFI_CIFP, rffi.VOIDP, rffi.VOIDP,
                                   rffi.CArrayPtr(rffi.VOIDP)], lltype.Void)

# XXX hardcode this values by now, we need some new logic/thinking for that

ffi_type_sint = lltype.malloc(FFI_TYPE_P.TO, flavor='raw', immortal=True)
ffi_type_sint.c_size = rffi.cast(size_t, 4)
ffi_type_sint.c_alignment = rffi.cast(rffi.USHORT, 4)
ffi_type_sint.c_type = rffi.cast(rffi.USHORT, 10)
ffi_type_sint.c_elements = lltype.nullptr(FFI_TYPE_PP.TO)

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

class FuncPtr:
    def __init__(self, func_sym):
        # xxx args here
        if not func_sym:
            raise OSError("NULL func_sym")
        self.func_sym = func_sym
        self.ll_cif = lltype.malloc(FFI_CIFP.TO, flavor='raw')
        res = c_ffi_prep_cif(self.ll_cif, rffi.cast(rffi.USHORT, FFI_DEFAULT_ABI),
                             rffi.cast(rffi.UINT, 0), ffi_type_sint, lltype.nullptr(FFI_TYPE_PP.TO))
        if not res == FFI_OK:
            raise OSError("Wrong typedef")

    def call(self, args):
        # allocated result should be padded and stuff
        PTR_T = lltype.Ptr(rffi.CFixedArray(rffi.INT, 1))
        result = lltype.malloc(PTR_T.TO, flavor='raw')
        c_ffi_call(self.ll_cif, self.func_sym, rffi.cast(rffi.VOIDP, result),
                   lltype.nullptr(rffi.CCHARPP.TO))
        res = result[0]
        lltype.free(result, flavor='raw')
        return res

    def __del__(self):
        lltype.free(self.ll_cif, flavor='raw')

class CDLL:
    def __init__(self, libname):
        self.lib = dlopen(libname)

    def __del__(self):
        c_dlclose(self.lib)

    def getpointer(self, name):
        return FuncPtr(dlsym(self.lib, name))
