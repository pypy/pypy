from pypy.interpreter.error import OperationError
from pypy.rlib.objectmodel import specialize
from pypy.rlib import runicode
from pypy.module._codecs import interp_codecs

@specialize.memo()
def decode_error_handler(space):
    def raise_unicode_exception_decode(errors, encoding, msg, s,
                                       startingpos, endingpos):
        raise OperationError(space.w_UnicodeDecodeError,
                             space.newtuple([space.wrap(encoding),
                                             space.wrap(s),
                                             space.wrap(startingpos),
                                             space.wrap(endingpos),
                                             space.wrap(msg)]))
    return raise_unicode_exception_decode

@specialize.memo()
def encode_error_handler(space):
    def raise_unicode_exception_encode(errors, encoding, msg, u,
                                       startingpos, endingpos):
        raise OperationError(space.w_UnicodeEncodeError,
                             space.newtuple([space.wrap(encoding),
                                             space.wrap(u),
                                             space.wrap(startingpos),
                                             space.wrap(endingpos),
                                             space.wrap(msg)]))
    return raise_unicode_exception_encode

# ____________________________________________________________

def PyUnicode_AsEncodedString(space, w_data, w_encoding):
    return interp_codecs.encode(space, w_data, w_encoding)

# These functions take and return unwrapped rpython strings and unicodes
def PyUnicode_DecodeUnicodeEscape(space, string):
    state = space.fromcache(interp_codecs.CodecState)
    unicodedata_handler = state.get_unicodedata_handler(space)
    result, consumed = runicode.str_decode_unicode_escape(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space),
        unicodedata_handler=unicodedata_handler)
    return result

def PyUnicode_DecodeRawUnicodeEscape(space, string):
    result, consumed = runicode.str_decode_raw_unicode_escape(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space))
    return result

def PyUnicode_DecodeUTF8(space, string):
    result, consumed = runicode.str_decode_utf_8(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space),
        allow_surrogates=True)
    return result

def PyUnicode_EncodeUTF8(space, uni):
    return runicode.unicode_encode_utf_8(
        uni, len(uni), "strict",
        errorhandler=encode_error_handler(space),
        allow_surrogates=True)
