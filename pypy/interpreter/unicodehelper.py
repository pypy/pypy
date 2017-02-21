from pypy.interpreter.error import OperationError
from rpython.rlib.objectmodel import specialize
from rpython.rlib import runicode, rutf8
from pypy.module._codecs import interp_codecs

@specialize.memo()
def decode_error_handler(space):
    # Fast version of the "strict" errors handler.
    def raise_unicode_exception_decode(errors, encoding, msg, s,
                                       startingpos, endingpos):
        raise OperationError(space.w_UnicodeDecodeError,
                             space.newtuple([space.newtext(encoding),
                                             space.newbytes(s),
                                             space.newint(startingpos),
                                             space.newint(endingpos),
                                             space.newtext(msg)]))
    return raise_unicode_exception_decode

class RUnicodeEncodeError(Exception):
    def __init__(self, encoding, object, start, end, reason):
        self.encoding = encoding
        self.object = object
        self.start = start
        self.end = end
        self.reason = reason

def raise_unicode_exception_encode(errors, encoding, msg, u,
                                   startingpos, endingpos):
    raise RUnicodeEncodeError(encoding, u, startingpos, endingpos, msg)

# ____________________________________________________________

def encode(space, w_data, encoding=None, errors='strict'):
    from pypy.objspace.std.unicodeobject import encode_object
    return encode_object(space, w_data, encoding, errors)

# These functions take and return unwrapped rpython strings and unicodes
def decode_unicode_escape(space, string):
    state = space.fromcache(interp_codecs.CodecState)
    unicodedata_handler = state.get_unicodedata_handler(space)
    # XXX pick better length, maybe
    result, consumed, length = rutf8.str_decode_utf8_escape(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space),
        unicodedata_handler=unicodedata_handler)
    return result, length

def decode_raw_unicode_escape(space, string):
    # XXX pick better length, maybe
    result, consumed, length = rutf8.str_decode_raw_utf8_escape(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space))
    return result, length

def decode_utf8(space, string):
    # Surrogates are accepted and not treated specially at all.
    # If there happen to be two 3-bytes encoding a pair of surrogates,
    # you still get two surrogate unicode characters in the result.
    # These are the Python2 rules; Python3 differs.
    result, consumed = runicode.str_decode_utf_8(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space),
        allow_surrogates=True)
    return result

def encode_utf8(space, uni):
    # Note that this function never raises UnicodeEncodeError,
    # since surrogates are allowed, either paired or lone.
    # A paired surrogate is considered like the non-BMP character
    # it stands for.  These are the Python2 rules; Python3 differs.
    return runicode.unicode_encode_utf_8(
        uni, len(uni), "strict",
        errorhandler=raise_unicode_exception_encode,
        allow_surrogates=True)
