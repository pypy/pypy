import sys
from pypy.interpreter.error import OperationError
from rpython.rlib.objectmodel import specialize
from rpython.rlib import runicode
from pypy.module._codecs import interp_codecs
_WIN32 = sys.platform == 'win32'
_MACOSX = sys.platform == 'darwin'
if _WIN32:
    from rpython.rlib.runicode import str_decode_mbcs, unicode_encode_mbcs
else:
    # Workaround translator's confusion
    str_decode_mbcs = unicode_encode_mbcs = lambda *args, **kwargs: None

@specialize.memo()
def decode_error_handler(space):
    # Fast version of the "strict" errors handler.
    def raise_unicode_exception_decode(errors, encoding, msg, s,
                                       startingpos, endingpos):
        raise OperationError(space.w_UnicodeDecodeError,
                             space.newtuple([space.wrap(encoding),
                                             space.newbytes(s),
                                             space.wrap(startingpos),
                                             space.wrap(endingpos),
                                             space.wrap(msg)]))
    return raise_unicode_exception_decode

@specialize.memo()
def encode_error_handler(space):
    # Fast version of the "strict" errors handler.
    def raise_unicode_exception_encode(errors, encoding, msg, u,
                                       startingpos, endingpos):
        raise OperationError(space.w_UnicodeEncodeError,
                             space.newtuple([space.wrap(encoding),
                                             space.wrap(u),
                                             space.wrap(startingpos),
                                             space.wrap(endingpos),
                                             space.wrap(msg)]))
    return raise_unicode_exception_encode

class RUnicodeEncodeError(Exception):
    def __init__(self, encoding, object, start, end, reason):
        self.encoding = encoding
        self.object = object
        self.start = start
        self.end = end
        self.reason = reason

@specialize.memo()
def rpy_encode_error_handler():
    # A RPython version of the "strict" error handler.
    def raise_unicode_exception_encode(errors, encoding, msg, u,
                                       startingpos, endingpos):
        raise RUnicodeEncodeError(encoding, u, startingpos, endingpos, msg)
    return raise_unicode_exception_encode

# ____________________________________________________________

def fsdecode(space, w_string):
    state = space.fromcache(interp_codecs.CodecState)
    if _WIN32:
        bytes = space.bytes_w(w_string)
        uni = str_decode_mbcs(bytes, len(bytes), 'strict',
                              errorhandler=decode_error_handler(space),
                              force_ignore=False)[0]
    elif _MACOSX:
        bytes = space.bytes_w(w_string)
        uni = runicode.str_decode_utf_8(
            bytes, len(bytes), 'surrogateescape',
            errorhandler=state.decode_error_handler)[0]
    elif space.sys.filesystemencoding is None or state.codec_need_encodings:
        # bootstrap check: if the filesystemencoding isn't initialized
        # or the filesystem codec is implemented in Python we cannot
        # use it before the codecs are ready. use the locale codec
        # instead
        from pypy.module._codecs.locale import (
            str_decode_locale_surrogateescape)
        bytes = space.bytes_w(w_string)
        uni = str_decode_locale_surrogateescape(
            bytes, errorhandler=decode_error_handler(space))
    else:
        from pypy.module.sys.interp_encoding import getfilesystemencoding
        return space.call_method(w_string, 'decode',
                                 getfilesystemencoding(space),
                                 space.wrap('surrogateescape'))
    return space.wrap(uni)

def fsencode(space, w_uni):
    state = space.fromcache(interp_codecs.CodecState)
    if _WIN32:
        uni = space.unicode_w(w_uni)
        bytes = unicode_encode_mbcs(uni, len(uni), 'strict',
                                    errorhandler=encode_error_handler(space),
                                    force_replace=False)
    elif _MACOSX:
        uni = space.unicode_w(w_uni)
        bytes = runicode.unicode_encode_utf_8(
            uni, len(uni), 'surrogateescape',
            errorhandler=state.encode_error_handler)
    elif space.sys.filesystemencoding is None or state.codec_need_encodings:
        # bootstrap check: if the filesystemencoding isn't initialized
        # or the filesystem codec is implemented in Python we cannot
        # use it before the codecs are ready. use the locale codec
        # instead
        from pypy.module._codecs.locale import (
            unicode_encode_locale_surrogateescape)
        uni = space.unicode_w(w_uni)
        bytes = unicode_encode_locale_surrogateescape(
            uni, errorhandler=encode_error_handler(space))
    else:
        from pypy.module.sys.interp_encoding import getfilesystemencoding
        return space.call_method(w_uni, 'encode',
                                 getfilesystemencoding(space),
                                 space.wrap('surrogateescape'))
    return space.newbytes(bytes)

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

def decode_utf8(space, string, allow_surrogates=False):
    result, consumed = runicode.str_decode_utf_8(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space),
        allow_surrogates=allow_surrogates)
    return result

def encode_utf8(space, uni, allow_surrogates=False):
    # Note that Python3 tends to forbid lone surrogates
    return runicode.unicode_encode_utf_8(
        uni, len(uni), "strict",
        errorhandler=encode_error_handler(space),
        allow_surrogates=allow_surrogates)
