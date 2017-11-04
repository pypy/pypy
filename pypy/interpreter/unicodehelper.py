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
    def raise_unicode_exception_encode(errors, encoding, msg, w_u,
                                       startingpos, endingpos):
        raise OperationError(space.w_UnicodeEncodeError,
                             space.newtuple([space.newtext(encoding),
                                             w_u,
                                             space.newint(startingpos),
                                             space.newint(endingpos),
                                             space.newtext(msg)]))
    return raise_unicode_exception_encode

def convert_arg_to_w_unicode(space, w_arg, strict=None):
    from pypy.objspace.std.unicodeobject import W_UnicodeObject
    assert not hasattr(space, 'is_fake_objspace')
    return W_UnicodeObject.convert_arg_to_w_unicode(space, w_arg, strict)

# ____________________________________________________________

def encode(space, w_data, encoding=None, errors='strict'):
    from pypy.objspace.std.unicodeobject import encode_object
    return encode_object(space, w_data, encoding, errors)

def _has_surrogate(u):
    for c in u:
        if 0xDB80 <= ord(c) <= 0xCBFF or 0xD800 <= ord(c) <= 0xDB7F:
            return True
    return False

def _get_flag(u):
    flag = rutf8.FLAG_ASCII
    for c in u:
        if 0xDB80 <= ord(c) <= 0xCBFF or 0xD800 <= ord(c) <= 0xDB7F:
            return rutf8.FLAG_HAS_SURROGATES
        if ord(c) >= 0x80:
            flag = rutf8.FLAG_REGULAR
    return flag

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
    utf8 = ''.join([u.encode('utf8') for u in result_u])
    if rutf8.first_non_ascii_char(utf8) == -1:
        flag = rutf8.FLAG_ASCII
    elif _has_surrogate(result_u):
        flag = rutf8.FLAG_HAS_SURROGATES
    else:
        flag = rutf8.FLAG_REGULAR
    return utf8, len(result_u), flag

def decode_raw_unicode_escape(space, string):
    # XXX pick better length, maybe
    # XXX that guy does not belong in runicode (nor in rutf8)
    result_u, consumed = runicode.str_decode_raw_unicode_escape(
        string, len(string), "strict",
        final=True, errorhandler=DecodeWrapper(decode_error_handler(space)).handle)
    # XXX argh.  we want each surrogate to be encoded separately
    utf8 = ''.join([u.encode('utf8') for u in result_u])
    if rutf8.first_non_ascii_char(utf8) == -1:
        flag = rutf8.FLAG_ASCII
    elif _has_surrogate(result_u):
        flag = rutf8.FLAG_HAS_SURROGATES
    else:
        flag = rutf8.FLAG_REGULAR
    return utf8, len(result_u), flag

def check_ascii_or_raise(space, string):
    try:
        rutf8.check_ascii(string)
    except rutf8.CheckError as e:
        decode_error_handler(space)('strict', 'ascii',
                                    'ordinal not in range(128)', string,
                                    e.pos, e.pos + 1)
        assert False, "unreachable"

def check_utf8_or_raise(space, string):
    # Surrogates are accepted and not treated specially at all.
    # If there happen to be two 3-bytes encoding a pair of surrogates,
    # you still get two surrogate unicode characters in the result.
    # These are the Python2 rules; Python3 differs.
    try:
        length, flag = rutf8.check_utf8(string, allow_surrogates=True)
    except rutf8.CheckError as e:
        decode_error_handler(space)('strict', 'utf8', 'invalid utf-8', string,
                                    e.pos, e.pos + 1)
        assert False, "unreachable"
    return length, flag

def encode_utf8(space, uni):
    # DEPRECATED
    # Note that this function never raises UnicodeEncodeError,
    # since surrogates are allowed, either paired or lone.
    # A paired surrogate is considered like the non-BMP character
    # it stands for.  These are the Python2 rules; Python3 differs.
    return runicode.unicode_encode_utf_8(
        uni, len(uni), "strict",
        errorhandler=None,
        allow_surrogates=True)

def decode_utf8(space, s):
    # DEPRECATED
    return (s, check_utf8_or_raise(space, s))

def utf8_encode_ascii(utf8, utf8len, errors, errorhandler):
    if len(utf8) == utf8len:
        return utf8
    # No Way At All to emulate the calls to the error handler in
    # less than three pages, so better not.
    u = utf8.decode("utf8")
    w = EncodeWrapper(errorhandler)
    return runicode.unicode_encode_ascii(u, len(u), errors, w.handle)

def str_decode_ascii(s, slen, errors, final, errorhandler):
    try:
        rutf8.check_ascii(s)
        return s, slen, len(s)
    except rutf8.CheckError:
        w = DecodeWrapper((errorhandler))
        u, pos = runicode.str_decode_ascii(s, slen, errors, final, w.handle)
        return u.encode('utf8'), pos, len(u), _get_flag(u)

# XXX wrappers, think about speed

class DecodeWrapper(object):
    def __init__(self, handler):
        self.orig = handler

    def handle(self, errors, encoding, msg, s, pos, endpos):
        return self.orig(errors, encoding, msg, s, pos, endpos)

class EncodeWrapper(object):
    def __init__(self, handler):
        self.orig = handler

    def handle(self, errors, encoding, msg, s, pos, endpos):
        return self.orig(errors, encoding, msg, s.encode("utf8"), pos, endpos)

# some irregular interfaces
def str_decode_utf8(s, slen, errors, final, errorhandler):
    w = DecodeWrapper(errorhandler)
    u, pos = runicode.str_decode_utf_8_impl(s, slen, errors, final, w.handle,
        runicode.allow_surrogate_by_default)
    return u.encode('utf8'), pos, len(u), _get_flag(u)

def str_decode_unicode_escape(s, slen, errors, final, errorhandler, ud_handler):
    w = DecodeWrapper(errorhandler)
    u, pos = runicode.str_decode_unicode_escape(s, slen, errors, final,
                                                w.handle,
                                                ud_handler)
    return u.encode('utf8'), pos, len(u), _get_flag(u)

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
        w = DecodeWrapper((errorhandler))
        u, pos = getattr(runicode, decoder_name)(s, slen, errors, final, w.handle)
        return u.encode('utf8'), pos, len(u), _get_flag(u)
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
