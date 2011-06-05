from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import NoneNotWrapped, interp2app, unwrap_spec
from pypy.rlib.rstring import StringBuilder, UnicodeBuilder
from pypy.rlib.objectmodel import we_are_translated

class CodecState(object):
    def __init__(self, space):
        self.codec_search_path = []
        self.codec_search_cache = {}
        self.codec_error_registry = {}
        self.codec_need_encodings = True
        self.decode_error_handler = self.make_errorhandler(space, True)
        self.encode_error_handler = self.make_errorhandler(space, False)

        self.unicodedata_handler = None

    def make_errorhandler(self, space, decode):
        def unicode_call_errorhandler(errors,  encoding, reason, input,
                                      startpos, endpos):

            w_errorhandler = lookup_error(space, errors)
            if decode:
                w_cls = space.w_UnicodeDecodeError
            else:
                w_cls = space.w_UnicodeEncodeError
            w_exc =  space.call_function(
                w_cls,
                space.wrap(encoding),
                space.wrap(input),
                space.wrap(startpos),
                space.wrap(endpos),
                space.wrap(reason))
            w_res = space.call_function(w_errorhandler, w_exc)
            if (not space.is_true(space.isinstance(w_res, space.w_tuple))
                or space.len_w(w_res) != 2):
                if decode:
                    msg = ("decoding error handler must return "
                           "(unicode, int) tuple, not %s")
                else:
                    msg = ("encoding error handler must return "
                           "(unicode, int) tuple, not %s")
                raise operationerrfmt(
                    space.w_TypeError, msg,
                    space.str_w(space.repr(w_res)))
            w_replace, w_newpos = space.fixedview(w_res, 2)
            newpos = space.int_w(w_newpos)
            if (newpos < 0):
                newpos = len(input) + newpos
            if newpos < 0 or newpos > len(input):
                raise operationerrfmt(
                    space.w_IndexError,
                    "position %d from error handler out of bounds", newpos)
            if decode:
                replace = space.unicode_w(w_replace)
                return replace, newpos
            else:
                from pypy.objspace.std.unicodetype import encode_object
                w_str = encode_object(space, w_replace, encoding, None)
                replace = space.str_w(w_str)
                return replace, newpos
        return unicode_call_errorhandler

    def get_unicodedata_handler(self, space):
        if self.unicodedata_handler:
            return self.unicodedata_handler
        try:
            w_builtin = space.getbuiltinmodule('__builtin__')
            w_import = space.getattr(w_builtin, space.wrap("__import__"))
            w_unicodedata = space.call_function(w_import,
                                                space.wrap("unicodedata"))
            w_getcode = space.getattr(w_unicodedata, space.wrap("_get_code"))
        except OperationError:
            return None
        else:
            self.unicodedata_handler = UnicodeData_Handler(space, w_getcode)
            return self.unicodedata_handler

    def _freeze_(self):
        assert not self.codec_search_path
        return False

def register_codec(space, w_search_function):
    """register(search_function)

    Register a codec search function. Search functions are expected to take
    one argument, the encoding name in all lower case letters, and return
    a tuple of functions (encoder, decoder, stream_reader, stream_writer).
    """
    state = space.fromcache(CodecState)
    if space.is_true(space.callable(w_search_function)):
        state.codec_search_path.append(w_search_function)
    else:
        raise OperationError(
            space.w_TypeError,
            space.wrap("argument must be callable"))


@unwrap_spec(encoding=str)
def lookup_codec(space, encoding):
    """lookup(encoding) -> (encoder, decoder, stream_reader, stream_writer)
    Looks up a codec tuple in the Python codec registry and returns
    a tuple of functions.
    """
    assert not (space.config.translating and not we_are_translated()), \
        "lookup_codec() should not be called during translation"
    state = space.fromcache(CodecState)
    normalized_encoding = encoding.replace(" ", "-").lower()
    w_result = state.codec_search_cache.get(normalized_encoding, None)
    if w_result is not None:
        return w_result
    if state.codec_need_encodings:
        w_import = space.getattr(space.builtin, space.wrap("__import__"))
        # registers new codecs
        space.call_function(w_import, space.wrap("encodings"))
        state.codec_need_encodings = False
        if len(state.codec_search_path) == 0:
            raise OperationError(
                space.w_LookupError,
                space.wrap("no codec search functions registered: "
                           "can't find encoding"))
    for w_search in state.codec_search_path:
        w_result = space.call_function(w_search,
                                       space.wrap(normalized_encoding))
        if not space.is_w(w_result, space.w_None):
            if not (space.is_true(space.isinstance(w_result,
                                            space.w_tuple)) and
                    space.len_w(w_result) == 4):
                raise OperationError(
                    space.w_TypeError,
                    space.wrap("codec search functions must return 4-tuples"))
            else:
                state.codec_search_cache[normalized_encoding] = w_result
                return w_result
    raise operationerrfmt(
        space.w_LookupError,
        "unknown encoding: %s", encoding)

# ____________________________________________________________
# Register standard error handlers

def check_exception(space, w_exc):
    try:
        w_start = space.getattr(w_exc, space.wrap('start'))
        w_end = space.getattr(w_exc, space.wrap('end'))
        w_obj = space.getattr(w_exc, space.wrap('object'))
    except OperationError, e:
        if not e.match(space, space.w_AttributeError):
            raise
        raise OperationError(space.w_TypeError, space.wrap(
            "wrong exception"))

    delta = space.int_w(w_end) - space.int_w(w_start)
    if delta < 0 or not (space.isinstance_w(w_obj, space.w_str) or
                         space.isinstance_w(w_obj, space.w_unicode)):
        raise OperationError(space.w_TypeError, space.wrap(
            "wrong exception"))

def strict_errors(space, w_exc):
    check_exception(space, w_exc)
    if space.isinstance_w(w_exc, space.w_BaseException):
        raise OperationError(space.type(w_exc), w_exc)
    else:
        raise OperationError(space.w_TypeError, space.wrap(
            "codec must pass exception instance"))

def ignore_errors(space, w_exc):
    check_exception(space, w_exc)
    w_end = space.getattr(w_exc, space.wrap('end'))
    if space.isinstance_w(w_exc, space.w_UnicodeEncodeError):
        return space.newtuple([space.wrap(''), w_end])
    elif (space.isinstance_w(w_exc, space.w_UnicodeDecodeError) or
          space.isinstance_w(w_exc, space.w_UnicodeTranslateError)):
        return space.newtuple([space.wrap(u''), w_end])
    else:
        typename = space.type(w_exc).getname(space, '?')
        raise operationerrfmt(space.w_TypeError,
            "don't know how to handle %s in error callback", typename)

def replace_errors(space, w_exc):
    check_exception(space, w_exc)
    w_start = space.getattr(w_exc, space.wrap('start'))
    w_end = space.getattr(w_exc, space.wrap('end'))
    size = space.int_w(w_end) - space.int_w(w_start)
    if space.isinstance_w(w_exc, space.w_UnicodeEncodeError):
        text = '?' * size
        return space.newtuple([space.wrap(text), w_end])
    elif space.isinstance_w(w_exc, space.w_UnicodeDecodeError):
        text = u'\ufffd'
        return space.newtuple([space.wrap(text), w_end])
    elif space.isinstance_w(w_exc, space.w_UnicodeTranslateError):
        text = u'\ufffd' * size
        return space.newtuple([space.wrap(text), w_end])
    else:
        typename = space.type(w_exc).getname(space, '?')
        raise operationerrfmt(space.w_TypeError,
            "don't know how to handle %s in error callback", typename)

def xmlcharrefreplace_errors(space, w_exc):
    check_exception(space, w_exc)
    if space.isinstance_w(w_exc, space.w_UnicodeEncodeError):
        obj = space.realunicode_w(space.getattr(w_exc, space.wrap('object')))
        start = space.int_w(space.getattr(w_exc, space.wrap('start')))
        w_end = space.getattr(w_exc, space.wrap('end'))
        end = space.int_w(w_end)
        builder = UnicodeBuilder()
        pos = start
        while pos < end:
            ch = obj[pos]
            builder.append(u"&#")
            builder.append(unicode(str(ord(ch))))
            builder.append(u";")
            pos += 1
        return space.newtuple([space.wrap(builder.build()), w_end])
    else:
        typename = space.type(w_exc).getname(space, '?')
        raise operationerrfmt(space.w_TypeError,
            "don't know how to handle %s in error callback", typename)

def backslashreplace_errors(space, w_exc):
    check_exception(space, w_exc)
    if space.isinstance_w(w_exc, space.w_UnicodeEncodeError):
        obj = space.realunicode_w(space.getattr(w_exc, space.wrap('object')))
        start = space.int_w(space.getattr(w_exc, space.wrap('start')))
        w_end = space.getattr(w_exc, space.wrap('end'))
        end = space.int_w(w_end)
        builder = UnicodeBuilder()
        pos = start
        while pos < end:
            oc = ord(obj[pos])
            num = hex(oc)
            if (oc >= 0x10000):
                builder.append(u"\\U")
                zeros = 8
            elif (oc >= 0x100):
                builder.append(u"\\u")
                zeros = 4
            else:
                builder.append(u"\\x")
                zeros = 2
            lnum = len(num)
            nb = zeros + 2 - lnum # num starts with '0x'
            if nb > 0:
                builder.append_multiple_char(u'0', nb)
            builder.append_slice(unicode(num), 2, lnum)
            pos += 1
        return space.newtuple([space.wrap(builder.build()), w_end])
    else:
        typename = space.type(w_exc).getname(space, '?')
        raise operationerrfmt(space.w_TypeError,
            "don't know how to handle %s in error callback", typename)

def register_builtin_error_handlers(space):
    "NOT_RPYTHON"
    state = space.fromcache(CodecState)
    for error in ("strict", "ignore", "replace", "xmlcharrefreplace",
                  "backslashreplace"):
        name = error + "_errors"
        state.codec_error_registry[error] = space.wrap(interp2app(globals()[name]))


@unwrap_spec(errors=str)
def lookup_error(space, errors):
    """lookup_error(errors) -> handler

    Return the error handler for the specified error handling name
    or raise a LookupError, if no handler exists under this name.
    """

    state = space.fromcache(CodecState)
    try:
        w_err_handler = state.codec_error_registry[errors]
    except KeyError:
        raise operationerrfmt(
            space.w_LookupError,
            "unknown error handler name %s", errors)
    return w_err_handler


@unwrap_spec(errors=str)
def encode(space, w_obj, w_encoding=NoneNotWrapped, errors='strict'):
    """encode(obj, [encoding[,errors]]) -> object

    Encodes obj using the codec registered for encoding. encoding defaults
    to the default encoding. errors may be given to set a different error
    handling scheme. Default is 'strict' meaning that encoding errors raise
    a ValueError. Other possible values are 'ignore', 'replace' and
    'xmlcharrefreplace' as well as any other name registered with
    codecs.register_error that can handle ValueErrors.
    """
    if w_encoding is None:
        encoding = space.sys.defaultencoding
    else:
        encoding = space.str_w(w_encoding)
    w_encoder = space.getitem(lookup_codec(space, encoding), space.wrap(0))
    w_res = space.call_function(w_encoder, w_obj, space.wrap(errors))
    return space.getitem(w_res, space.wrap(0))

@unwrap_spec(s='bufferstr', errors='str_or_None')
def buffer_encode(space, s, errors='strict'):
    return space.newtuple([space.wrap(s), space.wrap(len(s))])

@unwrap_spec(errors=str)
def decode(space, w_obj, w_encoding=NoneNotWrapped, errors='strict'):
    """decode(obj, [encoding[,errors]]) -> object

    Decodes obj using the codec registered for encoding. encoding defaults
    to the default encoding. errors may be given to set a different error
    handling scheme. Default is 'strict' meaning that encoding errors raise
    a ValueError. Other possible values are 'ignore' and 'replace'
    as well as any other name registerd with codecs.register_error that is
    able to handle ValueErrors.
    """
    if w_encoding is None:
        encoding = space.sys.defaultencoding
    else:
        encoding = space.str_w(w_encoding)
    w_decoder = space.getitem(lookup_codec(space, encoding), space.wrap(1))
    if space.is_true(w_decoder):
        w_res = space.call_function(w_decoder, w_obj, space.wrap(errors))
        if (not space.is_true(space.isinstance(w_res, space.w_tuple))
            or space.len_w(w_res) != 2):
            raise OperationError(
                space.w_TypeError,
                space.wrap("encoder must return a tuple (object, integer)"))
        return space.getitem(w_res, space.wrap(0))
    else:
        assert 0, "XXX, what to do here?"

@unwrap_spec(errors=str)
def register_error(space, errors, w_handler):
    """register_error(errors, handler)

    Register the specified error handler under the name
    errors. handler must be a callable object, that
    will be called with an exception instance containing
    information about the location of the encoding/decoding
    error and must return a (replacement, new position) tuple.
    """
    state = space.fromcache(CodecState)
    if space.is_true(space.callable(w_handler)):
        state.codec_error_registry[errors] = w_handler
    else:
        raise OperationError(
            space.w_TypeError,
            space.wrap("handler must be callable"))

# ____________________________________________________________
# delegation to runicode

from pypy.rlib import runicode

def make_raw_encoder(name):
    rname = "unicode_encode_%s" % (name.replace("_encode", ""), )
    assert hasattr(runicode, rname)
    def raw_encoder(space, uni):
        state = space.fromcache(CodecState)
        func = getattr(runicode, rname)
        errors = "strict"
        return func(uni, len(uni), errors, state.encode_error_handler)
    raw_encoder.func_name = rname
    return raw_encoder

def make_raw_decoder(name):
    rname = "str_decode_%s" % (name.replace("_decode", ""), )
    assert hasattr(runicode, rname)
    def raw_decoder(space, string):
        final = True
        errors = "strict"
        state = space.fromcache(CodecState)
        func = getattr(runicode, rname)
        kwargs = {}
        if name == 'unicode_escape':
            unicodedata_handler = state.get_unicodedata_handler(space)
            result, consumed = func(string, len(string), errors,
                                    final, state.decode_error_handler,
                                    unicodedata_handler=unicodedata_handler)
        else:
            result, consumed = func(string, len(string), errors,
                                    final, state.decode_error_handler)
        return result
    raw_decoder.func_name = rname
    return raw_decoder

def make_encoder_wrapper(name):
    rname = "unicode_encode_%s" % (name.replace("_encode", ""), )
    assert hasattr(runicode, rname)
    @unwrap_spec(uni=unicode, errors='str_or_None')
    def wrap_encoder(space, uni, errors="strict"):
        if errors is None:
            errors = 'strict'
        state = space.fromcache(CodecState)
        func = getattr(runicode, rname)
        result = func(uni, len(uni), errors, state.encode_error_handler)
        return space.newtuple([space.wrap(result), space.wrap(len(uni))])
    wrap_encoder.func_name = rname
    globals()[name] = wrap_encoder

def make_decoder_wrapper(name):
    rname = "str_decode_%s" % (name.replace("_decode", ""), )
    assert hasattr(runicode, rname)
    @unwrap_spec(string='bufferstr', errors='str_or_None')
    def wrap_decoder(space, string, errors="strict", w_final=False):
        if errors is None:
            errors = 'strict'
        final = space.is_true(w_final)
        state = space.fromcache(CodecState)
        func = getattr(runicode, rname)
        result, consumed = func(string, len(string), errors,
                                final, state.decode_error_handler)
        return space.newtuple([space.wrap(result), space.wrap(consumed)])
    wrap_decoder.func_name = rname
    globals()[name] = wrap_decoder

for encoders in [
         "ascii_encode",
         "latin_1_encode",
         "utf_7_encode",
         "utf_8_encode",
         "utf_16_encode",
         "utf_16_be_encode",
         "utf_16_le_encode",
         "utf_32_encode",
         "utf_32_be_encode",
         "utf_32_le_encode",
         "unicode_escape_encode",
         "raw_unicode_escape_encode",
         "unicode_internal_encode",
        ]:
    make_encoder_wrapper(encoders)

for decoders in [
         "ascii_decode",
         "latin_1_decode",
         "utf_7_decode",
         "utf_8_decode",
         "utf_16_decode",
         "utf_16_be_decode",
         "utf_16_le_decode",
         "utf_32_decode",
         "utf_32_be_decode",
         "utf_32_le_decode",
         "raw_unicode_escape_decode",
         ]:
    make_decoder_wrapper(decoders)

if hasattr(runicode, 'str_decode_mbcs'):
    make_encoder_wrapper('mbcs_encode')
    make_decoder_wrapper('mbcs_decode')

@unwrap_spec(data=str, errors='str_or_None', byteorder=int)
def utf_16_ex_decode(space, data, errors='strict', byteorder=0, w_final=False):
    if errors is None:
        errors = 'strict'
    final = space.is_true(w_final)
    state = space.fromcache(CodecState)
    if byteorder == 0:
        byteorder = 'native'
    elif byteorder == -1:
        byteorder = 'little'
    else:
        byteorder = 'big'
    consumed = len(data)
    if final:
        consumed = 0
    res, consumed, byteorder = runicode.str_decode_utf_16_helper(
        data, len(data), errors, final, state.decode_error_handler, byteorder)
    return space.newtuple([space.wrap(res), space.wrap(consumed),
                           space.wrap(byteorder)])

@unwrap_spec(data=str, errors='str_or_None', byteorder=int)
def utf_32_ex_decode(space, data, errors='strict', byteorder=0, w_final=False):
    final = space.is_true(w_final)
    state = space.fromcache(CodecState)
    if byteorder == 0:
        byteorder = 'native'
    elif byteorder == -1:
        byteorder = 'little'
    else:
        byteorder = 'big'
    consumed = len(data)
    if final:
        consumed = 0
    res, consumed, byteorder = runicode.str_decode_utf_32_helper(
        data, len(data), errors, final, state.decode_error_handler, byteorder)
    return space.newtuple([space.wrap(res), space.wrap(consumed),
                           space.wrap(byteorder)])

# ____________________________________________________________
# Charmap

class Charmap_Decode:
    def __init__(self, space, w_mapping):
        self.space = space
        self.w_mapping = w_mapping

        # fast path for all the stuff in the encodings module
        if space.is_true(space.isinstance(w_mapping, space.w_tuple)):
            self.mapping_w = space.fixedview(w_mapping)
        else:
            self.mapping_w = None

    def get(self, ch, errorchar):
        space = self.space

        # get the character from the mapping
        if self.mapping_w is not None:
            w_ch = self.mapping_w[ord(ch)]
        else:
            try:
                w_ch = space.getitem(self.w_mapping, space.newint(ord(ch)))
            except OperationError, e:
                if not e.match(space, space.w_LookupError):
                    raise
                return errorchar

        # Charmap may return a unicode string
        try:
            x = space.unicode_w(w_ch)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
        else:
            return x

        # Charmap may return a number
        try:
            x = space.int_w(w_ch)
        except OperationError:
            if not e.match(space, space.w_TypeError):
                raise
        else:
            if 0 <= x < 65536: # Even on wide unicode builds...
                return unichr(x)
            else:
                raise OperationError(space.w_TypeError, space.wrap(
                    "character mapping must be in range(65536)"))

        # Charmap may return None
        if space.is_w(w_ch, space.w_None):
            return errorchar

        raise OperationError(space.w_TypeError, space.wrap("invalid mapping"))

class Charmap_Encode:
    def __init__(self, space, w_mapping):
        self.space = space
        self.w_mapping = w_mapping

    def get(self, ch, errorchar):
        space = self.space

        # get the character from the mapping
        try:
            w_ch = space.getitem(self.w_mapping, space.newint(ord(ch)))
        except OperationError, e:
            if not e.match(space, space.w_LookupError):
                raise
            return errorchar

        # Charmap may return a string
        try:
            x = space.realstr_w(w_ch)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
        else:
            return x

        # Charmap may return a number
        try:
            x = space.int_w(w_ch)
        except OperationError:
            if not e.match(space, space.w_TypeError):
                raise
        else:
            if 0 <= x < 256:
                return chr(x)
            else:
                raise OperationError(space.w_TypeError, space.wrap(
                    "character mapping must be in range(256)"))

        # Charmap may return None
        if space.is_w(w_ch, space.w_None):
            return errorchar

        raise OperationError(space.w_TypeError, space.wrap("invalid mapping"))


@unwrap_spec(string=str, errors='str_or_None')
def charmap_decode(space, string, errors="strict", w_mapping=None):
    if errors is None:
        errors = 'strict'
    if len(string) == 0:
        return space.newtuple([space.wrap(u''), space.wrap(0)])

    if space.is_w(w_mapping, space.w_None):
        mapping = None
    else:
        mapping = Charmap_Decode(space, w_mapping)

    final = True
    state = space.fromcache(CodecState)
    result, consumed = runicode.str_decode_charmap(
        string, len(string), errors,
        final, state.decode_error_handler, mapping)
    return space.newtuple([space.wrap(result), space.wrap(consumed)])

@unwrap_spec(uni=unicode, errors='str_or_None')
def charmap_encode(space, uni, errors="strict", w_mapping=None):
    if errors is None:
        errors = 'strict'
    if space.is_w(w_mapping, space.w_None):
        mapping = None
    else:
        mapping = Charmap_Encode(space, w_mapping)

    state = space.fromcache(CodecState)
    result = runicode.unicode_encode_charmap(
        uni, len(uni), errors,
        state.encode_error_handler, mapping)
    return space.newtuple([space.wrap(result), space.wrap(len(uni))])


@unwrap_spec(chars=unicode)
def charmap_build(space, chars):
    # XXX CPython sometimes uses a three-level trie
    w_charmap = space.newdict()
    for num in range(len(chars)):
        elem = chars[num]
        space.setitem(w_charmap, space.newint(ord(elem)), space.newint(num))
    return w_charmap

# ____________________________________________________________
# Unicode escape

class UnicodeData_Handler:
    def __init__(self, space, w_getcode):
        self.space = space
        self.w_getcode = w_getcode

    def call(self, name):
        space = self.space
        try:
            w_code = space.call_function(self.w_getcode, space.wrap(name))
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                raise
            return -1
        return space.int_w(w_code)

@unwrap_spec(string='bufferstr', errors='str_or_None')
def unicode_escape_decode(space, string, errors="strict", w_final=False):
    if errors is None:
        errors = 'strict'
    final = space.is_true(w_final)
    state = space.fromcache(CodecState)
    errorhandler=state.decode_error_handler

    unicode_name_handler = state.get_unicodedata_handler(space)

    result, consumed = runicode.str_decode_unicode_escape(
        string, len(string), errors,
        final, state.decode_error_handler,
        unicode_name_handler)

    return space.newtuple([space.wrap(result), space.wrap(consumed)])

# ____________________________________________________________
# Unicode-internal

@unwrap_spec(errors='str_or_None')
def unicode_internal_decode(space, w_string, errors="strict"):
    if errors is None:
        errors = 'strict'
    # special case for this codec: unicodes are returned as is
    if space.isinstance_w(w_string, space.w_unicode):
        return space.newtuple([w_string, space.len(w_string)])

    string = space.str_w(w_string)

    if len(string) == 0:
        return space.newtuple([space.wrap(u''), space.wrap(0)])

    final = True
    state = space.fromcache(CodecState)
    result, consumed = runicode.str_decode_unicode_internal(
        string, len(string), errors,
        final, state.decode_error_handler)
    return space.newtuple([space.wrap(result), space.wrap(consumed)])

# ____________________________________________________________
# support for the "string escape" codec
# This is a bytes-to bytes transformation

@unwrap_spec(errors='str_or_None')
def escape_encode(space, w_string, errors='strict'):
    w_repr = space.repr(w_string)
    w_result = space.getslice(w_repr, space.wrap(1), space.wrap(-1))
    return space.newtuple([w_result, space.len(w_string)])

@unwrap_spec(data=str, errors='str_or_None')
def escape_decode(space, data, errors='strict'):
    from pypy.interpreter.pyparser.parsestring import PyString_DecodeEscape
    result = PyString_DecodeEscape(space, data, None)
    return space.newtuple([space.wrap(result), space.wrap(len(data))])
