import _cffi_backend

cffi_type_void    = _cffi_backend.new_void_type()
cffi_type_pointer = _cffi_backend.new_pointer_type(cffi_type_void)

cffi_type_char    = _cffi_backend.new_primitive_type("char")
cffi_type_schar   = _cffi_backend.new_primitive_type("signed char")
cffi_type_uchar   = _cffi_backend.new_primitive_type("unsigned char")
cffi_type_short   = _cffi_backend.new_primitive_type("short")
cffi_type_ushort  = _cffi_backend.new_primitive_type("unsigned short")
cffi_type_long    = _cffi_backend.new_primitive_type("long")
cffi_type_ulong   = _cffi_backend.new_primitive_type("unsigned long")
cffi_type_longlong   = _cffi_backend.new_primitive_type("long long")
cffi_type_ulonglong  = _cffi_backend.new_primitive_type("unsigned long long")
cffi_type_float   = _cffi_backend.new_primitive_type("float")
cffi_type_double  = _cffi_backend.new_primitive_type("double")
cffi_type_longdouble = _cffi_backend.new_primitive_type("long double")

cffi_type_short_p  = _cffi_backend.new_pointer_type(cffi_type_short)
cffi_type_ushort_p = _cffi_backend.new_pointer_type(cffi_type_ushort)
cffi_type_long_p   = _cffi_backend.new_pointer_type(cffi_type_long)
cffi_type_ulong_p  = _cffi_backend.new_pointer_type(cffi_type_ulong)

cffi_types = {
    'c': cffi_type_char,
    'b': cffi_type_schar,
    'B': cffi_type_uchar,
    'h': cffi_type_short,
    'H': cffi_type_ushort,
    'l': cffi_type_long,
    'L': cffi_type_ulong,
    'q': cffi_type_longlong,
    'Q': cffi_type_ulonglong,
    'f': cffi_type_float,
    'd': cffi_type_double,
    'g': cffi_type_longdouble,
    'z': cffi_type_pointer,
    'P': cffi_type_pointer,
    'O': cffi_type_pointer,
    }


def sizeof(tp_letter):
    return _cffi_backend.sizeof(cffi_types[tp_letter])

def alignment(tp_letter):
    return _cffi_backend.alignof(cffi_types[tp_letter])

class CDLL(object):
    def __init__(self, libname):
        if libname is None:
            from ctypes.util import find_library
            libname = find_library('c')
        self._cffi_library = _cffi_backend.load_library(libname)
        self.libname = libname

    def getaddressindll(self, name):
        return self._cffi_library.read_variable(cffi_type_pointer, name)

def get_libc():
    return CDLL(None)

FUNCFLAG_STDCALL   = 0    # on Windows: for WINAPI calls
FUNCFLAG_CDECL     = 1    # on Windows: for __cdecl calls
FUNCFLAG_PYTHONAPI = 4
FUNCFLAG_USE_ERRNO = 8
FUNCFLAG_USE_LASTERROR = 16

class DataInstance(object):
    pass

class Array(DataInstance):
    def __init__(self, shape):
        pass

class CallbackPtr(DataInstance):
    def __init__(self, *stuff):
        pass
