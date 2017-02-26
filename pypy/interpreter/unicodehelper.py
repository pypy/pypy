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
    # XXX that guy does not belong in runicode (nor in rutf8)
    result_u, consumed = runicode.str_decode_unicode_escape(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space),
        unicodedata_handler=unicodedata_handler)
    return result_u.encode('utf8'), len(result_u)

def decode_raw_unicode_escape(space, string):
    # XXX pick better length, maybe
    # XXX that guy does not belong in runicode (nor in rutf8)
    result_u, consumed = runicode.str_decode_raw_unicode_escape(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space))
    return result_u.encode('utf8'), len(result_u)

def check_utf8(space, string):
    # Surrogates are accepted and not treated specially at all.
    # If there happen to be two 3-bytes encoding a pair of surrogates,
    # you still get two surrogate unicode characters in the result.
    # These are the Python2 rules; Python3 differs.
    try:
        consumed, length = rutf8.str_check_utf8(string, len(string), True)
    except rutf8.Utf8CheckError as e:
        decode_error_handler(space)('strict', 'utf8', e.msg, string, e.startpos,
                                    e.endpos)
        raise False, "unreachable"
    return length

def encode_utf8(space, uni):
    # Note that this function never raises UnicodeEncodeError,
    # since surrogates are allowed, either paired or lone.
    # A paired surrogate is considered like the non-BMP character
    # it stands for.  These are the Python2 rules; Python3 differs.
    return runicode.unicode_encode_utf_8(
        uni, len(uni), "strict",
        errorhandler=raise_unicode_exception_encode,
        allow_surrogates=True)

def utf8_encode_ascii(utf8, utf8len, errors, errorhandler):
    if len(utf8) == utf8len:
        return utf8
    return rutf8.utf8_encode_ascii(utf8, errors, 'ascii',
                                   'ordinal not in range (128)',
                                   errorhandler)

def str_decode_ascii(s, slen, errors, final, errorhandler):
    try:
        rutf8.check_ascii(s)
        return s
    except rutf8.AsciiCheckError:
        return rutf8.str_decode_ascii(s, errors, errorhandler)

# XXX wrappers, think about speed

class DecodeWrapper(object):
    def __init__(self, handler):
        self.orig = handler

    def handle(self, errors, encoding, msg, s, pos, endpos):
        s, p, lgt = self.orig(errors, encoding, msg, s, pos, endpos)
        return s.decode("utf8"), p

class EncodeWrapper(object):
    def __init__(self, handler):
        self.orig = handler

    def handle(self, errors, encoding, msg, s, pos, endpos):
        s, rs, p, lgt = self.orig(errors, encoding, msg, s.encode("utf8"), pos, endpos)
        return s, rs, p

def utf8_encode_utf_7(utf8, utf8len, errors, errorhandler):
    u = utf8.decode("utf8")
    w = EncodeWrapper(errorhandler)
    return runicode.unicode_encode_utf_7(u, len(u), errors, w.handle)

def str_decode_utf_7(string, lgt, errors, final, errorhandler):
    w = DecodeWrapper(errorhandler)
    u, pos = runicode.str_decode_utf_7(string, lgt, errors, final, w.handle)
    return u.encode('utf8'), pos, len(u)

def str_decode_unicode_escape(s, slen, errors, final, errorhandler, ud_handler):
    w = DecodeWrapper(errorhandler)
    u, pos = runicode.str_decode_unicode_escape(s, slen, errors, final, w.handle,
                                                ud_handler)
    return u.encode('utf8'), pos, len(u)

def str_decode_raw_unicode_escape(s, slen, errors, final, errorhandler):
    w = DecodeWrapper(errorhandler)
    u, pos = runicode.str_decode_raw_unicode_escape(s, slen, errors, final,
                                                    w.handle)
    return u.encode('utf8'), pos, len(u)

def str_decode_utf8(s, slen, errors, final, errorhandler):
    w = DecodeWrapper(errorhandler)
    u, pos = runicode.str_decode_utf_8_impl(s, slen, errors, final, w.handle,
        runicode.allow_surrogate_by_default)
    return u.encode('utf8'), pos, len(u)

def utf8_encode_utf_16(utf8, utf8len, errors, errorhandler):
    w = EncodeWrapper(errorhandler)
    u = utf8.decode("utf8")
    return runicode.unicode_encode_utf_16(u, len(u), errors, w.handle)

def utf8_encode_latin_1(utf8, utf8len, errors, errorhandler):
    w = EncodeWrapper(errorhandler)
    u = utf8.decode("utf8")
    return runicode.unicode_encode_latin_1(u, len(u), errors, w.handle)
