from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, NoneNotWrapped
from pypy.interpreter.baseobjspace import W_Root

class CodecState(object):
    def __init__(self, space):
        self.codec_search_path = []
        self.codec_search_cache = {}
        self.codec_error_registry = {}
        self.codec_need_encodings = True
        self.error_handler = self.make_errorhandler(space)

    def make_errorhandler(self, space):
        def unicode_call_errorhandler(errors,  encoding, reason, input,
                                      startpos, endpos, decode=True):
            
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
            try:
                w_replace, w_newpos = space.unpacktuple(w_res, 2)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                raise OperationError(
                    space.w_TypeError,
                    space.wrap("encoding error handler must return "
                               "(unicode, int) tuple, not %s" % (
                                   space.str_w(space.repr(w_res)))))
            newpos = space.int_w(w_newpos)
            if (newpos < 0):
                newpos = len(input) + newpos
            if newpos < 0 or newpos > len(input):
                raise OperationError(
                    space.w_IndexError,
                    space.wrap("position %d from error handler "
                               "out of bounds" % newpos))
            if decode:
                replace = space.unicode_w(w_replace)
                return replace, newpos
            else:
                replace = space.str_w(w_replace)
                return replace, newpos
        unicode_call_errorhandler._annspecialcase_ = "specialize:arg(6)"
        return unicode_call_errorhandler


def register_codec(space, w_search_function):
    """register(search_function)
    
    Register a codec search function. Search functions are expected to take
    one argument, the encoding name in all lower case letters, and return
    a tuple of functions (encoder, decoder, stream_reader, stream_writer).
    """
    #import pdb; pdb.set_trace()
    state = space.fromcache(CodecState)
    if space.is_true(space.callable(w_search_function)):
        state.codec_search_path.append(w_search_function)
    else:
        raise OperationError(
            space.w_TypeError,
            space.wrap("argument must be callable"))
register_codec.unwrap_spec = [ObjSpace, W_Root]


def lookup_codec(space, encoding):
    """lookup(encoding) -> (encoder, decoder, stream_reader, stream_writer)
    Looks up a codec tuple in the Python codec registry and returns
    a tuple of functions.
    """
    #import pdb; pdb.set_trace()
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
            if not (space.is_true(space.is_(space.type(w_result),
                                            space.w_tuple)) and
                    space.int_w(space.len(w_result)) == 4):
                raise OperationError(
                    space.w_TypeError,
                    space.wrap("codec search functions must return 4-tuples"))
            else:
                state.codec_search_cache[normalized_encoding] = w_result 
                return w_result
    raise OperationError(
        space.w_LookupError,
        space.wrap("unknown encoding: %s" % encoding))
lookup_codec.unwrap_spec = [ObjSpace, str]
    

def lookup_error(space, errors):
    """lookup_error(errors) -> handler

    Return the error handler for the specified error handling name
    or raise a LookupError, if no handler exists under this name.
    """
    
    state = space.fromcache(CodecState)
    try:
        w_err_handler = state.codec_error_registry[errors]
    except KeyError:
        raise OperationError(
            space.w_LookupError,
            space.wrap("unknown error handler name %s" % errors))
    return w_err_handler
lookup_error.unwrap_spec = [ObjSpace, str]


def encode(space, w_obj, encoding=NoneNotWrapped, errors='strict'):
    """encode(obj, [encoding[,errors]]) -> object
    
    Encodes obj using the codec registered for encoding. encoding defaults
    to the default encoding. errors may be given to set a different error
    handling scheme. Default is 'strict' meaning that encoding errors raise
    a ValueError. Other possible values are 'ignore', 'replace' and
    'xmlcharrefreplace' as well as any other name registered with
    codecs.register_error that can handle ValueErrors.
    """
    #import pdb; pdb.set_trace()
    if encoding is None:
        encoding = space.sys.defaultencoding
    w_encoder = space.getitem(lookup_codec(space, encoding), space.wrap(0))
    if space.is_true(w_encoder):
        w_res = space.call_function(w_encoder, w_obj, space.wrap(errors))
        return space.getitem(w_res, space.wrap(0))
    else:
        assert 0, "XXX, what to do here?"
encode.unwrap_spec = [ObjSpace, W_Root, str, str]

def decode(space, w_obj, encoding=NoneNotWrapped, errors='strict'):
    """decode(obj, [encoding[,errors]]) -> object

    Decodes obj using the codec registered for encoding. encoding defaults
    to the default encoding. errors may be given to set a different error
    handling scheme. Default is 'strict' meaning that encoding errors raise
    a ValueError. Other possible values are 'ignore' and 'replace'
    as well as any other name registerd with codecs.register_error that is
    able to handle ValueErrors.
    """
    if encoding is None:
        encoding = space.sys.defaultencoding
    w_decoder = space.getitem(lookup_codec(space, encoding), space.wrap(1))
    if space.is_true(w_decoder):
        w_res = space.call_function(w_decoder, w_obj, space.wrap(errors))
        if (not space.is_true(space.isinstance(w_res, space.w_tuple))
            or space.int_w(space.len(w_res)) != 2):
            raise OperationError(
                space.w_TypeError,
                space.wrap("encoder must return a tuple (object, integer)"))
        return space.getitem(w_res, space.wrap(0))
    else:
        assert 0, "XXX, what to do here?"
decode.unwrap_spec = [ObjSpace, W_Root, str, str]

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
register_error.unwrap_spec = [ObjSpace, str, W_Root]

# ____________________________________________________________
# delegation to runicode

from pypy.rlib import runicode

def make_encoder_wrapper(name):
    rname = "unicode_encode_%s" % (name.replace("_encode", ""), )
    assert hasattr(runicode, rname)
    def wrap_encoder(space, uni, errors="strict"):
        state = space.fromcache(CodecState)
        func = getattr(runicode, rname)
        result = func(uni, len(uni), errors, state.error_handler)
        return space.newtuple([space.wrap(result), space.wrap(len(result))])
    wrap_encoder.unwrap_spec = [ObjSpace, unicode, str]
    globals()[name] = wrap_encoder

def make_decoder_wrapper(name):
    rname = "str_decode_%s" % (name.replace("_decode", ""), )
    assert hasattr(runicode, rname)
    def wrap_decoder(space, string, errors="strict", w_final=True):
        final = space.is_true(w_final)
        state = space.fromcache(CodecState)
        func = getattr(runicode, rname)
        result, consumed = func(string, len(string), errors,
                                final, state.error_handler)
        return space.newtuple([space.wrap(result), space.wrap(consumed)])
    wrap_decoder.unwrap_spec = [ObjSpace, str, str, W_Root]
    globals()[name] = wrap_decoder

for encoders in [
         "ascii_encode",
         "latin_1_encode",
         "utf_8_encode",
         "utf_16_encode",
         "utf_16_be_encode",
         "utf_16_le_encode",
        ]:
    make_encoder_wrapper(encoders)

for decoders in [
         "ascii_decode",
         "latin_1_decode",
         "utf_8_decode",
         "utf_16_decode",
         "utf_16_be_decode",
         "utf_16_le_decode",
         ]:
    make_decoder_wrapper(decoders)


def utf_16_ex_decode(space, data, errors='strict', byteorder=0, w_final=False):
    """None
    """
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
        data, len(data), errors, final, state.error_handler, byteorder)
    return space.newtuple([space.wrap(res), space.wrap(consumed),
                           space.wrap(byteorder)])
utf_16_ex_decode.unwrap_spec = [ObjSpace, str, str, int, W_Root]

