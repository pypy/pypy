import _cffi_backend

cffi_type_void    = _cffi_backend.new_void_type()
cffi_type_pointer = _cffi_backend.new_pointer_type(cffi_type_void)

cffi_type_char    = _cffi_backend.new_primitive_type("char")
cffi_type_schar   = _cffi_backend.new_primitive_type("signed char")
cffi_type_uchar   = _cffi_backend.new_primitive_type("unsigned char")
cffi_type_short   = _cffi_backend.new_primitive_type("short")
cffi_type_ushort  = _cffi_backend.new_primitive_type("unsigned short")
cffi_type_int     = _cffi_backend.new_primitive_type("int")
cffi_type_uint    = _cffi_backend.new_primitive_type("unsigned int")
cffi_type_long    = _cffi_backend.new_primitive_type("long")
cffi_type_ulong   = _cffi_backend.new_primitive_type("unsigned long")
cffi_type_longlong   = _cffi_backend.new_primitive_type("long long")
cffi_type_ulonglong  = _cffi_backend.new_primitive_type("unsigned long long")
cffi_type_float   = _cffi_backend.new_primitive_type("float")
cffi_type_double  = _cffi_backend.new_primitive_type("double")
cffi_type_longdouble = _cffi_backend.new_primitive_type("long double")
cffi_type_wchar_t = _cffi_backend.new_primitive_type("wchar_t")

cffi_type_short_p  = _cffi_backend.new_pointer_type(cffi_type_short)
cffi_type_ushort_p = _cffi_backend.new_pointer_type(cffi_type_ushort)
cffi_type_long_p   = _cffi_backend.new_pointer_type(cffi_type_long)
cffi_type_ulong_p  = _cffi_backend.new_pointer_type(cffi_type_ulong)

cffi_types = {
    'c': cffi_type_char,
    'b': cffi_type_schar,
    'B': cffi_type_uchar,
    'h': cffi_type_short,
    'u': cffi_type_wchar_t,
    'H': cffi_type_ushort,
    'i': cffi_type_int,
    'I': cffi_type_uint,
    'l': cffi_type_long,
    'L': cffi_type_ulong,
    'q': cffi_type_longlong,
    'Q': cffi_type_ulonglong,
    'f': cffi_type_float,
    'd': cffi_type_double,
    'g': cffi_type_longdouble,
    's' : cffi_type_pointer,
    'P' : cffi_type_pointer,
    'z' : cffi_type_pointer,
    'O' : cffi_type_pointer,
    'Z' : cffi_type_pointer,
    '?' : cffi_type_uchar,
    }

# ____________________________________________________________

def sizeof(tp_letter):
    return _cffi_backend.sizeof(cffi_types[tp_letter])

def alignment(tp_letter):
    return _cffi_backend.alignof(cffi_types[tp_letter])

FUNCFLAG_STDCALL   = 0    # on Windows: for WINAPI calls
FUNCFLAG_CDECL     = 1    # on Windows: for __cdecl calls
FUNCFLAG_PYTHONAPI = 4
FUNCFLAG_USE_ERRNO = 8
FUNCFLAG_USE_LASTERROR = 16

class CDLL(object):
    def __init__(self, libname):
        if libname is None:
            from ctypes.util import find_library
            libname = find_library('c')
        self._cffi_library = _cffi_backend.load_library(libname)
        self._libname = libname
        self._cache = {}

    def getaddressindll(self, name):
        return self._cffi_library.read_variable(cffi_type_pointer, name)

    def ptr(self, name, argtypes, restype, flags=FUNCFLAG_CDECL):
        """ Get a pointer for function name with provided argtypes
        and restype
        """
        key = name, tuple(argtypes), restype
        try:
            return self._cache[key]
        except KeyError:
            pass
        assert not argtypes
        if restype is None:
            cffi_restype = cffi_type_void
        else:
            cffi_restype = cffi_types[restype]
        assert isinstance(name, str)
        cffi_functype = _cffi_backend.new_function_type((), cffi_restype,
                                                        False)  # XXX abi
        cfunc = self._cffi_library.load_function(cffi_functype, name)
        funcptr = FuncPtr(cfunc)
        self._cache[key] = funcptr
        return funcptr

def get_libc():
    return CDLL('libc.so.6')    # XXX

class DataInstance(object):
    pass

class FuncPtr(object):
    def __init__(self, cfunc):
        self.cfunc = cfunc

# ____________________________________________________________

class Array(DataInstance):
    def __init__(self, shape):
        pass

# ____________________________________________________________

class CallbackPtr(DataInstance):
    def __init__(self, *stuff):
        pass
