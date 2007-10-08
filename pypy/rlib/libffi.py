
""" Various rpython-level functions for dlopen and libffi wrapping
"""

from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.unroll import unrolling_iterable

includes = ['dlfcn.h', 'ffi.h']

FFI_TYPE_P = lltype.Ptr(lltype.ForwardReference())
FFI_TYPE_PP = rffi.CArrayPtr(FFI_TYPE_P)

class CConfig:
    _includes_ = includes
    _libraries_ = ['ffi']

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

def add_simple_type(type_name):
    for name in ['size', 'alignment', 'type']:
        setattr(CConfig, type_name + '_' + name,
            rffi_platform.ConstantInteger(type_name + '.' + name))

def configure_simple_type(type_name):
    l = lltype.malloc(FFI_TYPE_P.TO, flavor='raw', immortal=True)
    for tp, name in [(size_t, 'size'),
                     (rffi.USHORT, 'alignment'),
                     (rffi.USHORT, 'type')]:
        value = getattr(cConfig, '%s_%s' % (type_name, name))
        setattr(l, 'c_' + name, rffi.cast(tp, value))
    l.c_elements = lltype.nullptr(FFI_TYPE_PP.TO)
    return l

base_names = ['double', 'uchar', 'schar', 'sshort', 'ushort', 'uint', 'sint',
              'ulong', 'slong', 'float', 'pointer', 'void']
type_names = ['ffi_type_%s' % name for name in base_names]
for i in type_names:
    add_simple_type(i)

class cConfig:
    pass

cConfig.__dict__.update(rffi_platform.configure(CConfig))

FFI_TYPE_P.TO.become(cConfig.ffi_type)
size_t = cConfig.size_t

for name in type_names:
    locals()[name] = configure_simple_type(name)

TYPE_MAP = {
    rffi.DOUBLE : ffi_type_double,
    rffi.FLOAT  : ffi_type_float,
    rffi.UCHAR  : ffi_type_uchar,
    rffi.CHAR   : ffi_type_schar,
    rffi.SHORT  : ffi_type_sshort,
    rffi.USHORT : ffi_type_ushort,
    rffi.UINT   : ffi_type_uint,
    rffi.INT    : ffi_type_sint,
    rffi.ULONG  : ffi_type_ulong,
    rffi.LONG   : ffi_type_slong,
    lltype.Void : ffi_type_void,
    # some shortcuts
    }

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
FFI_DEFAULT_ABI = rffi.cast(rffi.USHORT, cConfig.FFI_DEFAULT_ABI)
FFI_CIFP = rffi.COpaquePtr('ffi_cif', includes=includes)

VOIDPP = rffi.CArrayPtr(rffi.VOIDP)

c_ffi_prep_cif = external('ffi_prep_cif', [FFI_CIFP, rffi.USHORT, rffi.UINT,
                                           FFI_TYPE_P, FFI_TYPE_PP], rffi.INT)
c_ffi_call = external('ffi_call', [FFI_CIFP, rffi.VOIDP, rffi.VOIDP,
                                   VOIDPP], lltype.Void)

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
    def __init__(self, func_sym, argtypes, restype):
        argnum = len(argtypes)
        TP = rffi.CFixedArray(FFI_TYPE_P, argnum)
        self.ll_argtypes = lltype.malloc(TP, flavor='raw')
        self.argtypes = argtypes
        for i in unrolling_iterable(range(len(argtypes))):
            argtype = argtypes[i]
            self.ll_argtypes[i] = TYPE_MAP[argtype]
        TP = rffi.CFixedArray(rffi.VOIDP, argnum)
        self.ll_args = lltype.malloc(TP, flavor='raw')
        for i in range(argnum):
            # XXX
            TP = rffi.CFixedArray(argtypes[i], 1)
            self.ll_args[i] = rffi.cast(rffi.VOIDP,
                                        lltype.malloc(TP, flavor='raw'))
        self.restype = restype
        if restype is not None:
            TP = rffi.CFixedArray(restype, 1)
            self.ll_res = lltype.malloc(TP, flavor='raw')
        if not func_sym:
            raise OSError("NULL func_sym")
        self.func_sym = func_sym
        self.ll_cif = lltype.malloc(FFI_CIFP.TO, flavor='raw')
        res = c_ffi_prep_cif(self.ll_cif, FFI_DEFAULT_ABI,
                             rffi.cast(rffi.UINT, argnum),
                             TYPE_MAP[restype],
                             rffi.cast(FFI_TYPE_PP, self.ll_argtypes))
        if not res == FFI_OK:
            raise OSError("Wrong typedef")
    __init__._annspecialcase_ = 'specialize:arg(2, 3)'

    def call(self, args):
        # allocated result should be padded and stuff
        PTR_T = lltype.Ptr(rffi.CFixedArray(rffi.INT, 1))
        for i in range(len(args)):
            TP = lltype.Ptr(rffi.CFixedArray(self.argtypes[i], 1))
            addr = rffi.cast(TP, self.ll_args[i])
            addr[0] = args[i]
        c_ffi_call(self.ll_cif, self.func_sym,
                   rffi.cast(rffi.VOIDP, self.ll_res),
                   rffi.cast(VOIDPP, self.ll_args))
        return self.ll_res[0]
    call._annspecialcase_ = 'specialize:argtype(1)'

    def __del__(self):
        lltype.free(self.ll_argtypes, flavor='raw')
        lltype.free(self.ll_args, flavor='raw')
        lltype.free(self.ll_cif, flavor='raw')
        if self.restype is not None:
            lltype.free(self.ll_res, flavor='raw')

class CDLL:
    def __init__(self, libname):
        self.lib = dlopen(libname)

    def __del__(self):
        c_dlclose(self.lib)

    def getpointer(self, name, argtypes, restype):
        return FuncPtr(dlsym(self.lib, name), argtypes, restype)
    getpointer._annspecialcase_ = 'specialize:arg(2, 3)'
