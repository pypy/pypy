from pypy.interpreter.error import OperationError
from rpython.rlib.objectmodel import specialize
from rpython.rlib import runicode
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

def encode(space, w_data, encoding=None, errors='strict'):
    from pypy.objspace.std.unicodeobject import encode_object
    return encode_object(space, w_data, encoding, errors)

# These functions take and return unwrapped rpython strings and unicodes
def decode_unicode_escape(space, string):
    state = space.fromcache(interp_codecs.CodecState)
    unicodedata_handler = state.get_unicodedata_handler(space)
    result, consumed = runicode.str_decode_unicode_escape(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space),
        unicodedata_handler=unicodedata_handler)
    return result

def decode_raw_unicode_escape(space, string):
    result, consumed = runicode.str_decode_raw_unicode_escape(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space))
    return result

def decode_utf8(space, string):
    result, consumed = runicode.str_decode_utf_8(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space),
        allow_surrogates=True)
    return result

def encode_utf8(space, uni):
    return runicode.unicode_encode_utf_8(
        uni, len(uni), "strict",
        errorhandler=encode_error_handler(space),
        allow_surrogates=True)
