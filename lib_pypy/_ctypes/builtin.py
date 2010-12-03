
import _rawffi, sys

class ConvMode:
    encoding = 'ascii'
    errors = 'strict'

_memmove_addr = _rawffi.get_libc().getaddressindll('memmove')
_memset_addr = _rawffi.get_libc().getaddressindll('memset')

def _string_at(addr, lgt):
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

def _wstring_at(addr, lgt):
    import ctypes
    cobj = ctypes.c_void_p.from_param(addr)
    arg = cobj._get_buffer_value()
    # XXX purely applevel
    if lgt == -1:
        lgt = sys.maxint
    a = _rawffi.Array('u').fromaddress(arg, lgt)
    res = []
    for i in xrange(lgt):
        if lgt == sys.maxint and a[i] == '\x00':
            break
        res.append(a[i])
    return u''.join(res)
