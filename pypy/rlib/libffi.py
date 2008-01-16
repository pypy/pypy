
""" Various rpython-level functions for dlopen and libffi wrapping
"""

from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import we_are_translated
from pypy.tool.autopath import pypydir
from pypy.translator.tool.cbuild import ExternalCompilationInfo
import py

includes = ['dlfcn.h', 'ffi.h']
include_dirs = []
pot_incl = py.path.local('/usr/include/libffi')
if pot_incl.check():
    include_dirs.append(str(pot_incl))
lib_dirs = []
pot_lib = py.path.local('/usr/lib/libffi')
if pot_lib.check():
    lib_dirs.append(str(pot_lib))

FFI_TYPE_P = lltype.Ptr(lltype.ForwardReference())
FFI_TYPE_PP = rffi.CArrayPtr(FFI_TYPE_P)

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes = includes,
        libraries = ['ffi', 'dl'],
        include_dirs = include_dirs,
        library_dirs = lib_dirs,
    )

    RTLD_LOCAL = rffi_platform.DefinedConstantInteger('RTLD_LOCAL')
    RTLD_GLOBAL = rffi_platform.DefinedConstantInteger('RTLD_GLOBAL')
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
              'ulong', 'slong', 'float', 'pointer', 'void',
              # by size
              'sint8', 'uint8', 'sint16', 'uint16', 'sint32', 'uint32',
              'sint64', 'uint64']
type_names = ['ffi_type_%s' % name for name in base_names]
for i in type_names:
    add_simple_type(i)

class cConfig:
    pass

for k, v in rffi_platform.configure(CConfig).items():
    setattr(cConfig, k, v)

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
    }

def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result,
                           compilation_info=CConfig._compilation_info_, **kwds)

c_dlopen = external('dlopen', [rffi.CCHARP, rffi.INT], rffi.VOIDP,
                    _nowrapper=True)
c_dlclose = external('dlclose', [rffi.VOIDP], rffi.INT)
c_dlerror = external('dlerror', [], rffi.CCHARP)
c_dlsym = external('dlsym', [rffi.VOIDP, rffi.CCHARP], rffi.VOIDP)

RTLD_LOCAL = cConfig.RTLD_LOCAL
RTLD_GLOBAL = cConfig.RTLD_GLOBAL
RTLD_NOW = cConfig.RTLD_NOW
FFI_OK = cConfig.FFI_OK
FFI_BAD_TYPEDEF = cConfig.FFI_BAD_TYPEDEF
FFI_DEFAULT_ABI = rffi.cast(rffi.USHORT, cConfig.FFI_DEFAULT_ABI)
FFI_CIFP = rffi.COpaquePtr('ffi_cif', compilation_info=CConfig._compilation_info_)

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
    res = c_dlopen(name, rffi.cast(rffi.INT, mode))
    if not res:
        raise OSError(-1, dlerror())
    return res

def dlsym(libhandle, name):
    """ Wrapper around C-level dlsym
    """
    res = c_dlsym(libhandle, name)
    if not res:
        raise KeyError(name)
    # XXX rffi.cast here...
    return res

def cast_type_to_ffitype(tp):
    """ This function returns ffi representation of rpython type tp
    """
    return TYPE_MAP[tp]
cast_type_to_ffitype._annspecialcase_ = 'specialize:memo'

def push_arg_as_ffiptr(ffitp, arg, ll_buf):
    # this is for primitive types. For structures and arrays
    # would be something different (more dynamic)
    TP = lltype.typeOf(arg)
    TP_P = lltype.Ptr(rffi.CArray(TP))
    buf = rffi.cast(TP_P, ll_buf)
    buf[0] = arg
push_arg_as_ffiptr._annspecialcase_ = 'specialize:argtype(1)'

def check_pointer_type(TP):
    pass

class AbstractFuncPtr(object):
    ll_cif = lltype.nullptr(FFI_CIFP.TO)
    ll_argtypes = lltype.nullptr(FFI_TYPE_PP.TO)

    def __init__(self, name, argtypes, restype, funcsym):
        self.name = name
        self.argtypes = argtypes
        self.restype = restype
        self.funcsym = funcsym
        argnum = len(argtypes)
        self.ll_argtypes = lltype.malloc(FFI_TYPE_PP.TO, argnum, flavor='raw')
        for i in range(argnum):
            self.ll_argtypes[i] = argtypes[i]
        # XXX why cast to FFI_TYPE_PP is needed? ll2ctypes bug?
        self.ll_cif = lltype.malloc(FFI_CIFP.TO, flavor='raw')
        res = c_ffi_prep_cif(self.ll_cif, FFI_DEFAULT_ABI,
                             rffi.cast(rffi.UINT, argnum), restype,
                             rffi.cast(FFI_TYPE_PP, self.ll_argtypes))
        if not res == FFI_OK:
            raise OSError(-1, "Wrong typedef")

    def __del__(self):
        if self.ll_cif:
            lltype.free(self.ll_cif, flavor='raw')
        if self.ll_argtypes:
            lltype.free(self.ll_argtypes, flavor='raw')


class RawFuncPtr(AbstractFuncPtr):

    def call(self, args_ll, ll_result):
        assert len(args_ll) == len(self.argtypes), (
            "wrong number of arguments in call to %s(): "
            "%d instead of %d" % (self.name, len(args_ll), len(self.argtypes)))
        ll_args = lltype.malloc(rffi.VOIDPP.TO, len(args_ll), flavor='raw')
        for i in range(len(args_ll)):
            ll_args[i] = args_ll[i]
        c_ffi_call(self.ll_cif, self.funcsym, ll_result, ll_args)
        lltype.free(ll_args, flavor='raw')


class FuncPtr(AbstractFuncPtr):
    ll_args = lltype.nullptr(rffi.VOIDPP.TO)
    ll_result = lltype.nullptr(rffi.VOIDP.TO)

    def __init__(self, name, argtypes, restype, funcsym):
        # initialize each one of pointers with null
        AbstractFuncPtr.__init__(self, name, argtypes, restype, funcsym)
        self.argnum = len(self.argtypes)
        self.pushed_args = 0
        self.ll_args = lltype.malloc(rffi.VOIDPP.TO, self.argnum, flavor='raw')
        for i in range(self.argnum):
            # space for each argument
            self.ll_args[i] = lltype.malloc(rffi.VOIDP.TO,
                                            intmask(argtypes[i].c_size),
                                            flavor='raw')
        if restype != ffi_type_void:
            self.ll_result = lltype.malloc(rffi.VOIDP.TO,
                                           intmask(restype.c_size),
                                           flavor='raw')

    def push_arg(self, value):
        if self.pushed_args == self.argnum:
            raise TypeError("Too much arguments, eats %d, pushed %d" %
                            (self.argnum, self.argnum + 1))
        if not we_are_translated():
            TP = lltype.typeOf(value)
            if isinstance(TP, lltype.Ptr):
                if TP.TO._gckind != 'raw':
                    raise ValueError("Can only push raw values to C, not 'gc'")
                # XXX probably we should recursively check for struct fields
                # here, lets just ignore that for now
                if isinstance(TP.TO, lltype.Array):
                    try:
                        TP.TO._hints['nolength']
                    except KeyError:
                        raise ValueError("Can only push to C arrays without length info")
        push_arg_as_ffiptr(self.argtypes[self.pushed_args], value,
                           self.ll_args[self.pushed_args])
        self.pushed_args += 1
    push_arg._annspecialcase_ = 'specialize:argtype(1)'

    def _check_args(self):
        if self.pushed_args < self.argnum:
            raise TypeError("Did not specify arg nr %d" % (self.pushed_args + 1))

    def _clean_args(self):
        self.pushed_args = 0

    def call(self, RES_TP):
        self._check_args()
        c_ffi_call(self.ll_cif, self.funcsym,
                   rffi.cast(rffi.VOIDP, self.ll_result),
                   rffi.cast(VOIDPP, self.ll_args))
        if RES_TP is not lltype.Void:
            TP = lltype.Ptr(rffi.CArray(RES_TP))
            res = rffi.cast(TP, self.ll_result)[0]
        else:
            res = None
        self._clean_args()
        return res
    call._annspecialcase_ = 'specialize:arg(1)'

    def __del__(self):
        if self.ll_args:
            argnum = len(self.argtypes)
            for i in range(argnum):
                if self.ll_args[i]:
                    lltype.free(self.ll_args[i], flavor='raw')
            lltype.free(self.ll_args, flavor='raw')
        if self.ll_result:
            lltype.free(self.ll_result, flavor='raw')
        AbstractFuncPtr.__del__(self)

class CDLL:
    def __init__(self, libname):
        self.ll_libname = lltype.nullptr(rffi.CCHARP.TO)
        self.lib = lltype.nullptr(rffi.CCHARP.TO)
        self.ll_libname = rffi.str2charp(libname)
        self.lib = dlopen(self.ll_libname)

    def __del__(self):
        if self.lib:
            c_dlclose(self.lib)
        if self.ll_libname:
            lltype.free(self.ll_libname, flavor='raw')

    def getpointer(self, name, argtypes, restype):
        # these arguments are already casted to proper ffi
        # structures!
        return FuncPtr(name, argtypes, restype, dlsym(self.lib, name))

    def getrawpointer(self, name, argtypes, restype):
        # these arguments are already casted to proper ffi
        # structures!
        return RawFuncPtr(name, argtypes, restype, dlsym(self.lib, name))
