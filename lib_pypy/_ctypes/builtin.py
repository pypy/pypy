
import _rawffi, sys
try:
    from thread import _local as local
except ImportError:
    local = object    # no threads

class ConvMode:
    encoding = 'ascii'
    errors = 'strict'

_memmove_addr = _rawffi.get_libc().getaddressindll('memmove')
_memset_addr = _rawffi.get_libc().getaddressindll('memset')

def _string_at_addr(addr, lgt):
    # address here can be almost anything
    import ctypes
    cobj = ctypes.c_void_p.from_param(addr)
    arg = cobj._get_buffer_value()
    return _rawffi.charp2rawstring(arg, lgt)

def set_conversion_mode(encoding, errors):
    old_cm = ConvMode.encoding, ConvMode.errors
    ConvMode.errors = errors
    ConvMode.encoding = encoding
    return old_cm

def _wstring_at_addr(addr, lgt):
    import ctypes
    cobj = ctypes.c_void_p.from_param(addr)
    arg = cobj._get_buffer_value()
    return _rawffi.wcharp2rawunicode(arg, lgt)

class ErrorObject(local):
    def __init__(self):
        self.errno = 0
        self.winerror = 0
_error_object = ErrorObject()

def get_errno():
    return _error_object.errno

def set_errno(errno):
    old_errno = _error_object.errno
    _error_object.errno = errno
    return old_errno

def get_last_error():
    return _error_object.winerror

def set_last_error(winerror):
    old_winerror = _error_object.winerror
    _error_object.winerror = winerror
    return old_winerror
