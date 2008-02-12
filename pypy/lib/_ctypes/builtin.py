
import _rawffi, sys

class ConvMode:
    encoding = 'ascii'
    errors = 'strict'

_memmove_addr = ('memmove', 'libc.so.6')
_memset_addr = ('memset', 'libc.so.6')

def _string_at_addr(addr, lgt):
    # address here can be almost anything
    import ctypes
    obj = ctypes.c_char_p._CData_input(addr)[0]
    return _rawffi.charp2rawstring(obj, lgt)

def set_conversion_mode(encoding, errors):
    old_cm = ConvMode.encoding, ConvMode.errors
    ConvMode.errors = errors
    ConvMode.encoding = encoding
    return old_cm

def _wstring_at_addr(addr, lgt):
    import ctypes
    obj = ctypes.c_wchar_p._CData_input(addr)[0]
    # XXX purely applevel
    if lgt == -1:
        lgt = sys.maxint
    a = _rawffi.Array('u').fromaddress(obj, lgt)
    res = []
    for i in xrange(lgt):
        if lgt == sys.maxint and a[i] == '\x00':
            break
        res.append(a[i])
    return u''.join(res)
