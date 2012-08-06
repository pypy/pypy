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

cffi_cache_ptr = {cffi_type_void: cffi_type_pointer}
cffi_cache_array = {}
cffi_types_ptr = {}
cffi_types_array = {}
cffi_types_array_1 = {}

for _tp, _type in cffi_types.items():
    if _type not in cffi_cache_ptr:
        cffi_cache_ptr[_type] = _cffi_backend.new_pointer_type(_type)
    if _type not in cffi_cache_array:
        cffi_cache_array[_type] = _cffi_backend.new_array_type(
            cffi_cache_ptr[_type], None)
    cffi_types_ptr[_tp] = cffi_cache_ptr[_type]
    cffi_types_array[_tp] = cffi_cache_array[_type]
    cffi_types_array_1[_tp] = _cffi_backend.new_array_type(
        cffi_cache_ptr[_type], 1)

# ____________________________________________________________

def sizeof(tp_letter):
    return _cffi_backend.sizeof(cffi_types[tp_letter])

def alignment(tp_letter):
    return _cffi_backend.alignof(cffi_types[tp_letter])

def charp2string(address, maxlength=-1):
    xxxxxx

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
        cffi_argtypes = [cffi_types[tp] for tp in argtypes]
        if restype is None:
            cffi_restype = cffi_type_void
            ResultArray = None
        else:
            cffi_restype = cffi_types[restype]
            ResultArray = Array(restype)
        assert isinstance(name, str)
        cffi_functype = _cffi_backend.new_function_type(
            tuple(cffi_argtypes), cffi_restype, False)  # XXX abi
        cfunc = self._cffi_library.load_function(cffi_functype, name)
        funcptr = FuncPtr(cfunc, ResultArray)
        self._cache[key] = funcptr
        return funcptr

def get_libc():
    return CDLL('libc.so.6')    # XXX

class DataInstance(object):
    pass

class FuncPtr(object):
    def __init__(self, cfunc, ResultArray):
        self._cfunc = cfunc
        self._ResultArray = ResultArray

    def __call__(self, *args):
        result = self._cfunc(*[arg._prepare_arg() for arg in args])
        if self._ResultArray is None:
            return None
        return self._ResultArray(1, [result])

# ____________________________________________________________

class Array(object):
    def __init__(self, shape):
        self._cffi_item = cffi_types[shape]
        self._cffi_ptr = cffi_types_ptr[shape]
        self._cffi_array = cffi_types_array[shape]
        self._cffi_array_1 = cffi_types_array_1[shape]
        self._shape = shape

    def __call__(self, length, items=None, autofree=False):
        if length == 1:
            array = self._cffi_array_1
        else:
            # XXX cache 'array'?
            array = _cffi_backend.new_array_type(self._cffi_ptr, length)
        #
        return ArrayInstance(_cffi_backend.newp(array, items))

_array_of_pointers = Array('P')

class ArrayInstance(DataInstance):
    def __init__(self, cdata):
        self._cdata = cdata

    def byptr(self):
        return _array_of_pointers(1, [self._cdata])

    def __getitem__(self, index):
        return self._cdata[index]

    def __setitem__(self, index, value):
        self._cdata[index] = value

    def __getslice__(self, i, j):
        #if ...
        #    raise TypeError("only 'c' arrays support slicing")
        if i < 0: i = 0
        if j > len(self._cdata): j = len(self._cdata)
        if i > j: j = i
        return _cffi_backend.buffer(self._cdata + i, j - i)[:]

    def __setslice__(self, i, j, value):
        #if ...
        #    raise TypeError("only 'c' arrays support slicing")
        if i < 0: i = 0
        if j > len(self._cdata): j = len(self._cdata)
        if i > j: j = i
        _cffi_backend.buffer(self._cdata + i, j - i)[:] = value

    def _prepare_arg(self):
        if len(self._cdata) != 1:
            return TypeError("Argument should be an array of length 1, "
                             "got length %d" % len(self._cdata))
        # XXX check type
        return self._cdata[0]

    def free(self):
        pass  # XXX

# ____________________________________________________________

class CallbackPtr(DataInstance):
    def __init__(self, *stuff):
        pass
