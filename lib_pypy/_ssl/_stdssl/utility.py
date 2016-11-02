from _openssl import ffi
from _openssl import lib

def _string_from_asn1(asn1):
    data = lib.ASN1_STRING_data(asn1)
    length = lib.ASN1_STRING_length(asn1)
    return _str_with_len(ffi.cast("char*",data), length)

def _str_with_len(char_ptr, length):
    return ffi.buffer(char_ptr, length)[:].decode('utf-8')
