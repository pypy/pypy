
import _rawffi, sys

_memmove_addr = ('memmove', 'libc.so.6')
_memset_addr = ('memset', 'libc.so.6')

def _string_at_addr(addr, lgt):
    # address here can be almost anything
    import ctypes
    obj = ctypes.c_char_p._CData_input(addr)[0]
    return _rawffi.charp2rawstring(obj, lgt)

