from pypy.interpreter.error import OperationError
from rpython.rlib.objectmodel import specialize
from rpython.rlib import runicode, rutf8
from rpython.rlib.rstring import StringBuilder
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

@specialize.memo()
def encode_error_handler(space):
    # Fast version of the "strict" errors handler.
    def raise_unicode_exception_encode(errors, encoding, msg, u, u_len,
                                       startingpos, endingpos):
        raise OperationError(space.w_UnicodeEncodeError,
                             space.newtuple([space.newtext(encoding),
                                             space.newutf8(u, u_len),
                                             space.newint(startingpos),
                                             space.newint(endingpos),
                                             space.newtext(msg)]))
    return raise_unicode_exception_encode

def convert_arg_to_w_unicode(space, w_arg, strict=None):
    from pypy.objspace.std.unicodeobject import W_UnicodeObject
    return W_UnicodeObject.convert_arg_to_w_unicode(space, w_arg, strict)

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
        final=True, errorhandler=DecodeWrapper(decode_error_handler(space)).handle,
        unicodedata_handler=unicodedata_handler)
    # XXX argh.  we want each surrogate to be encoded separately
    return ''.join([u.encode('utf8') for u in result_u]), len(result_u)

def decode_raw_unicode_escape(space, string):
    # XXX pick better length, maybe
    # XXX that guy does not belong in runicode (nor in rutf8)
    result_u, consumed = runicode.str_decode_raw_unicode_escape(
        string, len(string), "strict",
        final=True, errorhandler=DecodeWrapper(decode_error_handler(space)).handle)
    # XXX argh.  we want each surrogate to be encoded separately
    return ''.join([u.encode('utf8') for u in result_u]), len(result_u)

def check_utf8(space, string):
    # Surrogates are accepted and not treated specially at all.
    # If there happen to be two 3-bytes encoding a pair of surrogates,
    # you still get two surrogate unicode characters in the result.
    # These are the Python2 rules; Python3 differs.
    try:
        length = rutf8.check_utf8(string, allow_surrogates=True)
    except rutf8.CheckError as e:
        XXX
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
        errorhandler=None,
        allow_surrogates=True)

def decode_utf8(space, s):
    u, _ = runicode.str_decode_utf_8(s, len(s),
        "strict", final=True,
        errorhandler=decode_error_handler(space),
        allow_surrogates=True)
    return u.encode('utf8'), len(u)

def utf8_encode_ascii(utf8, utf8len, errors, errorhandler):
    if len(utf8) == utf8len:
        return utf8
    assert False, "implement"
    b = StringBuilder(utf8len)
    i = 0
    lgt = 0
    while i < len(utf8):
        c = ord(utf8[i])
        if c <= 0x7F:
            b.append(chr(c))
            lgt += 1
            i += 1
        else:
            utf8_repl, newpos, length = errorhandler(errors, 'ascii', 
                'ordinal not in range (128)', utf8, lgt, lgt + 1)
    return b.build(), lgt

def str_decode_ascii(s, slen, errors, final, errorhandler):
    try:
        rutf8.check_ascii(s, slen)
        return s, slen, len(s)
    except rutf8.AsciiCheckError:
        return rutf8.str_decode_ascii(s, slen, errors, errorhandler)

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

# some irregular interfaces
def str_decode_utf8(s, slen, errors, final, errorhandler):
    w = DecodeWrapper(errorhandler)
    u, pos = runicode.str_decode_utf_8_impl(s, slen, errors, final, w.handle,
        runicode.allow_surrogate_by_default)
    return u.encode('utf8'), pos, len(u)

def str_decode_unicode_escape(s, slen, errors, final, errorhandler, ud_handler):
    w = DecodeWrapper(errorhandler)
    u, pos = runicode.str_decode_unicode_escape(s, slen, errors, final, w.handle,
                                                ud_handler)
    return u.encode('utf8'), pos, len(u)

def setup_new_encoders(encoding):
    encoder_name = 'utf8_encode_' + encoding
    encoder_call_name = 'unicode_encode_' + encoding
    decoder_name = 'str_decode_' + encoding
    def encoder(utf8, utf8len, errors, errorhandler):
        u = utf8.decode("utf8")
        w = EncodeWrapper(errorhandler)
        return getattr(runicode, encoder_call_name)(u, len(u), errors,
                       w.handle)
    def decoder(s, slen, errors, final, errorhandler):
        w = DecodeWrapper(errorhandler)
        u, pos = getattr(runicode, decoder_name)(s, slen, errors, final, w.handle)
        return u.encode('utf8'), pos, len(u)
    encoder.__name__ = encoder_name
    decoder.__name__ = decoder_name
    if encoder_name not in globals():
        globals()[encoder_name] = encoder
    if decoder_name not in globals():
        globals()[decoder_name] = decoder

def setup():
    for encoding in ['utf_7', 'unicode_escape', 'raw_unicode_escape',
                     'utf_16', 'utf_16_le', 'utf_16_be', 'utf_32_le', 'utf_32',
                     'utf_32_be', 'latin_1', 'unicode_internal']:
        setup_new_encoders(encoding)

setup()
