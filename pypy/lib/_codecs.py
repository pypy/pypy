"""

   _codecs -- Provides access to the codec registry and the builtin
              codecs.

   This module should never be imported directly. The standard library
   module "codecs" wraps this builtin module for use within Python.

   The codec registry is accessible via:

     register(search_function) -> None

     lookup(encoding) -> (encoder, decoder, stream_reader, stream_writer)

   The builtin Unicode codecs use the following interface:

     <encoding>_encode(Unicode_object[,errors='strict']) -> 
         (string object, bytes consumed)

     <encoding>_decode(char_buffer_obj[,errors='strict']) -> 
        (Unicode object, bytes consumed)

   <encoding>_encode() interfaces also accept non-Unicode object as
   input. The objects are then converted to Unicode using
   PyUnicode_FromObject() prior to applying the conversion.

   These <encoding>s are available: utf_8, unicode_escape,
   raw_unicode_escape, unicode_internal, latin_1, ascii (7-bit),
   mbcs (on win32).


Written by Marc-Andre Lemburg (mal@lemburg.com).

Copyright (c) Corporation for National Research Initiatives.

"""
from pypy.lib.unicodecodec import *

#/* --- Registry ----------------------------------------------------------- */
codec_search_path = []
codec_search_cache = {}
codec_error_registry = {}

def codec_register( search_function ):
    """register(search_function)
    
    Register a codec search function. Search functions are expected to take
    one argument, the encoding name in all lower case letters, and return
    a tuple of functions (encoder, decoder, stream_reader, stream_writer).
    """

    if callable(search_function):
        codec_search_path.append(search_function)

register = codec_register

def codec_lookup(encoding):
    """lookup(encoding) -> (encoder, decoder, stream_reader, stream_writer)
    Looks up a codec tuple in the Python codec registry and returns
    a tuple of functions.
    """
    
    result = codec_search_cache.get(encoding,None)
    if not result:
        for search in codec_search_path:
            result=search(encoding)
            if result : break
    return result

lookup = codec_lookup

def lookup_error(errors):
    """lookup_error(errors) -> handler

    Return the error handler for the specified error handling name
    or raise a LookupError, if no handler exists under this name.
    """
    try:
        err_handler = codec_error_registry[errors]
    except KeyError:
        raise LookupError("unknown error handler name %s"%errors)
    return err_handler

def register_error(errors, handler):
    """register_error(errors, handler)

    Register the specified error handler under the name
    errors. handler must be a callable object, that
    will be called with an exception instance containing
    information about the location of the encoding/decoding
    error and must return a (replacement, new position) tuple.
    """
    if callable(handler):
        codec_error_registry[errors] = handler
    else:
        raise TypeError("handler must be callable")
    
def encode(v, encoding='defaultencoding',errors='strict'):
    """encode(obj, [encoding[,errors]]) -> object
    
    Encodes obj using the codec registered for encoding. encoding defaults
    to the default encoding. errors may be given to set a different error
    handling scheme. Default is 'strict' meaning that encoding errors raise
    a ValueError. Other possible values are 'ignore', 'replace' and
    'xmlcharrefreplace' as well as any other name registered with
    codecs.register_error that can handle ValueErrors.
    """
    
    encoder = lookup(encoding)[0]
    if encoder :
        res = encoder(v,errors)
    return res[0]

def decode(obj,encoding='defaultencoding',errors='strict'):
    """decode(obj, [encoding[,errors]]) -> object

    Decodes obj using the codec registered for encoding. encoding defaults
    to the default encoding. errors may be given to set a different error
    handling scheme. Default is 'strict' meaning that encoding errors raise
    a ValueError. Other possible values are 'ignore' and 'replace'
    as well as any other name registerd with codecs.register_error that is
    able to handle ValueErrors.
    """
    decoder = lookup(encoding)[1]
    if decoder:
        res = decoder(obj,errors)
    return res[0]

def latin_1_encode(inst,obj,errors='strict'):
    """None
    """
    res = PyUnicode_EncodeLatin1(obj,len(obj),errors)
    return res, len(res)
# XXX MBCS codec might involve ctypes ?
def mbcs_decode():
    """None
    """
    pass

def readbuffer_encode(inst,obj,errors='strict'):
    """None
    """
    res = str(obj)
    return res,len(res)

def escape_encode(inst,obj,errors='strict'):
    """None
    """
    s = repr(obj)
    v = s[1:-1]
    return v,len(v)
# XXX
def utf_8_decode(inst,data,errors='strict'):
    """None
    """
    pass
# XXX
def raw_unicode_escape_decode(inst,data,errors='strict'):
    """None
    """
    pass

def utf_7_decode(inst,data,errors='strict'):
    """None
    """
    unistr = PyUnicode_DecodeUTF7(data,errors='strict')
    return unistr,len(unistr)
# XXX
def unicode_escape_encode(inst,obj,errors='strict'):
    """None
    """
    pass
# XXX
def latin_1_decode(inst,data,errors='strict'):
    """None
    """
    pass
# XXX
def utf_16_decode(inst,data,errors='strict'):
    """None
    """
    pass
# XXX
def unicode_escape_decode(inst,data,errors='strict'):
    """None
    """
    pass

def ascii_decode(inst,data,errors='strict'):
    """None
    """
    res = PyUnicode_DecodeASCII(data,len(data),errors)
    return res,len(res)

def charmap_encode(obj,errors='strict',mapping='latin-1'):
    """None
    """
    res = PyUnicode_EncodeCharmap(obj,len(obj),mapping,errors)
    return res,len(res)

def unicode_internal_encode(inst,obj,errors='strict'):
    """None
    """
    if type(obj) == unicode:
        return obj, len(obj)
    else:
        return PyUnicode_FromUnicode(obj,size),size
# XXX
def utf_16_ex_decode(inst,data,errors='strict'):
    """None
    """
    pass
# XXX Check if this is right
def escape_decode(data,errors='strict'):
    """None
    """
    return data,len(data)

def charbuffer_encode(inst,obj,errors='strict'):
    """None
    """
    res = str(obj)
    return res,len(res)
# XXX
def charmap_decode(inst,data,errors='strict'):
    """None
    """
    pass

def utf_7_encode(inst,obj,errors='strict'):
    """None
    """
    obj = PyUnicode_FromObject(obj)
    return (PyUnicode_EncodeUTF7(PyUnicode_AS_UNICODE(obj),
					 PyUnicode_GET_SIZE(obj),
                     0,
                     0,
					 errors),
		    PyUnicode_GET_SIZE(obj))

def mbcs_encode(inst,obj,errors='strict'):
    """None
    """
    return (PyUnicode_EncodeMBCS(
			       PyUnicode_AS_UNICODE(obj), 
			       PyUnicode_GET_SIZE(obj),
			       errors),
		    PyUnicode_GET_SIZE(obj));
    

def ascii_encode(inst,obj,errors='strict'):
    """None
    """
    return (PyUnicode_EncodeASCII(
			       PyUnicode_AS_UNICODE(obj), 
			       PyUnicode_GET_SIZE(obj),
			       errors),
                PyUnicode_GET_SIZE(obj))

def utf_16_encode(inst,obj,errors='strict'):
    """None
    """
    u = PyUnicode_EncodeUTF16(obj,len(obj),errors)
    return u,len(u)

def raw_unicode_escape_encode(inst,obj,errors='strict'):
    """None
    """
    res = PyUnicode_EncodeRawUnicodeEscape(obj,len(obj))
    return res,len(res)
# XXX
def utf_8_encode(inst,obj,errors='strict'):
    """None
    """
    pass
# XXX
def utf_16_le_encode(inst,obj,errors='strict'):
    """None
    """
    pass
# XXX
def utf_16_be_encode(inst,obj,errors='strict'):
    """None
    """
    pass

def unicode_internal_decode(inst,unistr,errors='strict'):
    """None
    """
    if type(unistr) == unicode:
        return unistr,len(unistr)
    else:
        return unicode(unistr),len(unistr)
# XXX
def utf_16_le_decode(inst,data,errors='strict'):
    """None
    """
    pass
# XXX
def utf_16_be_decode(inst,data,errors='strict'):
    """None
    """
    pass

def strict_errors(exc):
    if isinstance(exc,Exception):
        raise exc
    else:
        raise TypeError("codec must pass exception instance")
    
def ignore_errors(exc):
    if type(exc) in [UnicodeEncodeError,UnicodeDecodeError,UnicodeTranslateError]:
        return u'',exc.end
    else:
        raise TypeError("don't know how to handle %.400s in error callback"%type(exc))
# XXX
def replace_errors(exc):
    if isinstance(exc,Exception):
        raise exc
    else:
        raise TypeError("codec must pass exception instance")
# XXX    
def xmlcharrefreplace_errors(exc):
    if isinstance(exc,Exception):
        raise exc
    else:
        raise TypeError("codec must pass exception instance")
    
def backslashreplace_errors(exc):
    if isinstance(exc,UnicodeEncodeError):
        p=['\\']
        for c in exc.object[exc.start:exc.end]:
            oc = ord(c)
            if (oc >= 0x00010000):
                p.append('U')
                p.append("%.8x" % ord(c))
            elif (oc >= 0x100):
                p.append('u')
                p.append("%.4x" % ord(c))
            else:
                p.append('x')
                p.append("%.2x" % ord(c))
        return u''.join(p),exc.end
    else:
        raise TypeError("don't know how to handle %.400s in error callback"%type(exc))

register_error("strict",strict_errors)
register_error("ignore",ignore_errors)
register_error("replace",replace_errors)
register_error("xmlcharrefreplace",xmlcharrefreplace_errors)
register_error("backslashreplace",backslashreplace_errors)