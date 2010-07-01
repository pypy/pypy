from pypy.module._codecs import interp_codecs

def PyUnicode_AsEncodedString(space, w_data, w_encoding):
    return interp_codecs.encode(space, w_data, w_encoding)

# These functions take and return unwrapped rpython strings and unicodes
PyUnicode_DecodeUnicodeEscape = interp_codecs.make_raw_decoder('unicode_escape')
PyUnicode_DecodeRawUnicodeEscape = interp_codecs.make_raw_decoder('raw_unicode_escape')
PyUnicode_DecodeUTF8 = interp_codecs.make_raw_decoder('utf_8')
PyUnicode_EncodeUTF8 = interp_codecs.make_raw_encoder('utf_8')
