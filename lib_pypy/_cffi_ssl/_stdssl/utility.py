import sys
from _openssl import ffi
from _openssl import lib

def _string_from_asn1(asn1):
    data = lib.ASN1_STRING_data(asn1)
    length = lib.ASN1_STRING_length(asn1)
    return _str_with_len(ffi.cast("char*",data), length)

def _str_with_len(char_ptr, length):
    return ffi.buffer(char_ptr, length)[:].decode('utf-8')

def _bytes_with_len(char_ptr, length):
    return ffi.buffer(char_ptr, length)[:]

def _str_to_ffi_buffer(view, zeroterm=False):
    # REVIEW unsure how to solve this. might be easy:
    # str does not support buffer protocol.
    # I think a user should really encode the string before it is 
    # passed here!
    if isinstance(view, str):
        enc = view.encode()
        if zeroterm:
            return ffi.from_buffer(enc + b'\x00')
        else:
            return ffi.from_buffer(enc)
    else:
        if isinstance(view, memoryview):
            # TODO pypy limitation StringBuffer does not allow
            # to get a raw address to the string!
            view = bytes(view)
        if zeroterm:
            return ffi.from_buffer(view + b'\x00')
        else:
            return ffi.from_buffer(view)

def _str_from_buf(buf):
    return ffi.string(buf).decode('utf-8')

def _cstr_decode_fs(buf):
#define CONVERT(info, target) { \
#        const char *tmp = (info); \
#        target = NULL; \
#        if (!tmp) { Py_INCREF(Py_None); target = Py_None; } \
#        else if ((target = PyUnicode_DecodeFSDefault(tmp)) == NULL) { \
#            target = PyBytes_FromString(tmp); } \
#        if (!target) goto error; \
#    }
    # REVIEW
    return ffi.string(buf).decode(sys.getfilesystemencoding())

