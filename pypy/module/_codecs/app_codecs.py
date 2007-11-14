# Note:
# This *is* now explicitly RPython.
# Please make sure not to break this.

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
#from unicodecodec import *

import sys

# XXX MBCS codec might involve ctypes ?
def mbcs_decode():
    """None
    """
    pass

def readbuffer_encode( obj, errors='strict'):
    """None
    """
    res = str(obj)
    return res, len(res)

def escape_encode( obj, errors='strict'):
    """None
    """
    s = repr(obj)
    v = s[1:-1]
    return v, len(v)

def raw_unicode_escape_decode( data, errors='strict'):
    """None
    """
    res = PyUnicode_DecodeRawUnicodeEscape(data, len(data), errors)
    res = u''.join(res)
    return res, len(res)

def utf_7_decode( data, errors='strict'):
    """None
    """
    res = PyUnicode_DecodeUTF7(data, len(data), errors)
    res = u''.join(res)
    return res, len(res)

def unicode_escape_encode( obj, errors='strict'):
    """None
    """
    res = unicodeescape_string(obj, len(obj), 0)
    res = ''.join(res)
    return res, len(res)

def unicode_escape_decode( data, errors='strict'):
    """None
    """
    res = PyUnicode_DecodeUnicodeEscape(data, len(data), errors)
    res = u''.join(res)
    return res, len(res)


def charmap_encode(obj, errors='strict', mapping='latin-1'):
    """None
    """

    res = PyUnicode_EncodeCharmap(obj, len(obj), mapping, errors)
    res = ''.join(res)
    return res, len(res)

if sys.maxunicode == 65535:
    unicode_bytes = 2
else:
    unicode_bytes = 4

def unicode_internal_encode( obj, errors='strict'):
    """None
    """
    if type(obj) == unicode:
        p = []
        t = [ord(x) for x in obj]
        for i in t:
            bytes = []
            for j in xrange(unicode_bytes):
                bytes += chr(i%256)
                i >>= 8
            if sys.byteorder == "big":
                bytes.reverse()
            p += bytes
        res = ''.join(p)
        return res, len(res)
    else:
        res = "You can do better than this" # XXX make this right
        return res, len(res)

def unicode_internal_decode( unistr, errors='strict'):
    """None
    """
    if type(unistr) == unicode:
        return unistr, len(unistr)
    else:
        p = []
        i = 0
        if sys.byteorder == "big":
            start = unicode_bytes - 1
            stop = -1
            step = -1
        else:
            start = 0
            stop = unicode_bytes
            step = 1
        while i < len(unistr)-unicode_bytes+1:
            t = 0
            h = 0
            for j in range(start, stop, step):
                t += ord(unistr[i+j])<<(h*8)
                h += 1
            i += unicode_bytes
            p += unichr(t)
        res = u''.join(p)
        return res, len(res)

# XXX needs error messages when the input is invalid
def escape_decode(data, errors='strict'):
    """None
    """
    l = len(data)
    i = 0
    res = []
    while i < l:
        
        if data[i] == '\\':
            i += 1
            if i >= l:
                raise ValueError("Trailing \\ in string")
            else:
                if data[i] == '\\':
                    res += '\\'
                elif data[i] == 'n':
                    res += '\n'
                elif data[i] == 't':
                    res += '\t'
                elif data[i] == 'r':
                    res += '\r'
                elif data[i] == 'b':
                    res += '\b'
                elif data[i] == '\'':
                    res += '\''
                elif data[i] == '\"':
                    res += '\"'
                elif data[i] == 'f':
                    res += '\f'
                elif data[i] == 'a':
                    res += '\a'
                elif data[i] == 'v':
                    res += '\v'
                elif '0' <= data[i] <= '9':
                    # emulate a strange wrap-around behavior of CPython:
                    # \400 is the same as \000 because 0400 == 256
                    octal = data[i:i+3]
                    res += chr(int(octal, 8) & 0xFF)
                    i += 2
                elif data[i] == 'x':
                    hexa = data[i+1:i+3]
                    res += chr(int(hexa, 16))
                    i += 2
        else:
            res += data[i]
        i += 1
    res = ''.join(res)    
    return res, len(res)

def charbuffer_encode( obj, errors='strict'):
    """None
    """
    res = str(obj)
    res = ''.join(res)
    return res, len(res)

def charmap_decode( data, errors='strict', mapping=None):
    """None
    """
    res = PyUnicode_DecodeCharmap(data, len(data), mapping, errors)
    res = ''.join(res)
    return res, len(res)


def utf_7_encode( obj, errors='strict'):
    """None
    """
    res = PyUnicode_EncodeUTF7(obj, len(obj), 0, 0, errors)
    res = ''.join(res)
    return res, len(res)

def mbcs_encode( obj, errors='strict'):
    """None
    """
    pass
##    return (PyUnicode_EncodeMBCS(
##                             (obj), 
##                             len(obj),
##                             errors),
##                  len(obj))
    

def raw_unicode_escape_encode( obj, errors='strict'):
    """None
    """
    res = PyUnicode_EncodeRawUnicodeEscape(obj, len(obj))
    res = ''.join(res)
    return res, len(res)

def strict_errors(exc):
    if isinstance(exc, Exception):
        raise exc
    else:
        raise TypeError("codec must pass exception instance")
    
def ignore_errors(exc):
    if isinstance(exc, UnicodeEncodeError):
        return u'', exc.end
    elif isinstance(exc, (UnicodeDecodeError, UnicodeTranslateError)):
        return u'', exc.end
    else: 
        raise TypeError("don't know how to handle %.400s in error callback"%exc)

Py_UNICODE_REPLACEMENT_CHARACTER = u"\ufffd"

def replace_errors(exc):
    if isinstance(exc, UnicodeEncodeError):
        return u'?'*(exc.end-exc.start), exc.end
    elif isinstance(exc, (UnicodeTranslateError, UnicodeDecodeError)):
        return Py_UNICODE_REPLACEMENT_CHARACTER*(exc.end-exc.start), exc.end
    else:
        raise TypeError("don't know how to handle %.400s in error callback"%exc)

def xmlcharrefreplace_errors(exc):
    if isinstance(exc, UnicodeEncodeError):
        res = []
        for ch in exc.object[exc.start:exc.end]:
            res += '&#'
            res += str(ord(ch))
            res += ';'
        return u''.join(res), exc.end
    else:
        raise TypeError("don't know how to handle %.400s in error callback"%type(exc))
    
def backslashreplace_errors(exc):
    if isinstance(exc, UnicodeEncodeError):
        p = []
        for c in exc.object[exc.start:exc.end]:
            p += '\\'
            oc = ord(c)
            if (oc >= 0x00010000):
                p += 'U'
                p += "%.8x" % ord(c)
            elif (oc >= 0x100):
                p += 'u'
                p += "%.4x" % ord(c)
            else:
                p += 'x'
                p += "%.2x" % ord(c)
        return u''.join(p), exc.end
    else:
        raise TypeError("don't know how to handle %.400s in error callback"%type(exc))


def _register_existing_errors():
    import _codecs
    _codecs.register_error("strict", strict_errors)
    _codecs.register_error("ignore", ignore_errors)
    _codecs.register_error("replace", replace_errors)
    _codecs.register_error("xmlcharrefreplace", xmlcharrefreplace_errors)
    _codecs.register_error("backslashreplace", backslashreplace_errors)

#  ----------------------------------------------------------------------

##import sys
##""" Python implementation of CPythons builtin unicode codecs.
##
##    Generally the functions in this module take a list of characters an returns 
##    a list of characters.
##    
##    For use in the PyPy project"""


## indicate whether a UTF-7 character is special i.e. cannot be directly
##       encoded:
##         0 - not special
##         1 - special
##         2 - whitespace (optional)
##         3 - RFC2152 Set O (optional)
    
utf7_special = [
    1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 1, 1, 2, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    2, 3, 3, 3, 3, 3, 3, 0, 0, 0, 3, 1, 0, 0, 0, 1,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3, 0,
    3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 1, 3, 3, 3,
    3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 1, 1,
]

    
def SPECIAL(c, encodeO, encodeWS):
    c = ord(c)
    return (c>127 or utf7_special[c] == 1) or \
            (encodeWS and (utf7_special[(c)] == 2)) or \
            (encodeO and (utf7_special[(c)] == 3))
def B64(n):
    return ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[(n) & 0x3f])
def B64CHAR(c):
    return (c.isalnum() or (c) == '+' or (c) == '/')
def UB64(c):
    if (c) == '+' :
        return 62 
    elif (c) == '/':
        return 63 
    elif (c) >= 'a':
        return ord(c) - 71 
    elif (c) >= 'A':
        return ord(c) - 65 
    else: 
        return ord(c) + 4

def ENCODE( ch, bits) :
    out = []
    while (bits >= 6):
        out +=  B64(ch >> (bits-6))
        bits -= 6 
    return out, bits

def PyUnicode_DecodeUTF7(s, size, errors):

    starts = s
    errmsg = ""
    inShift = 0
    bitsleft = 0
    charsleft = 0
    surrogate = 0
    p = []
    errorHandler = None
    exc = None

    if (size == 0):
        return unicode('')
    i = 0
    while i < size:
        
        ch = s[i]
        if (inShift):
            if ((ch == '-') or not B64CHAR(ch)):
                inShift = 0
                i += 1
                
                while (bitsleft >= 16):
                    outCh =  ((charsleft) >> (bitsleft-16)) & 0xffff
                    bitsleft -= 16
                    
                    if (surrogate):
                        ##            We have already generated an error for the high surrogate
                        ##            so let's not bother seeing if the low surrogate is correct or not 
                        surrogate = 0
                    elif (0xDC00 <= (outCh) and (outCh) <= 0xDFFF):
            ##             This is a surrogate pair. Unfortunately we can't represent 
            ##               it in a 16-bit character 
                        surrogate = 1
                        msg = "code pairs are not supported"
                        out, x = unicode_call_errorhandler(errors, 'utf-7', msg, s, i-1, i)
                        p += out
                        bitsleft = 0
                        break
                    else:
                        p +=  unichr(outCh )
                        #p += out
                if (bitsleft >= 6):
##                    /* The shift sequence has a partial character in it. If
##                       bitsleft < 6 then we could just classify it as padding
##                       but that is not the case here */
                    msg = "partial character in shift sequence"
                    out, x = unicode_call_errorhandler(errors, 'utf-7', msg, s, i-1, i)
                    
##                /* According to RFC2152 the remaining bits should be zero. We
##                   choose to signal an error/insert a replacement character
##                   here so indicate the potential of a misencoded character. */

##                /* On x86, a << b == a << (b%32) so make sure that bitsleft != 0 */
##                if (bitsleft and (charsleft << (sizeof(charsleft) * 8 - bitsleft))):
##                    raise UnicodeDecodeError, "non-zero padding bits in shift sequence"
                if (ch == '-') :
                    if ((i < size) and (s[i] == '-')) :
                        p +=  '-'
                        inShift = 1
                    
                elif SPECIAL(ch, 0, 0) :
                    raise  UnicodeDecodeError, "unexpected special character"
                        
                else:  
                    p +=  ch 
            else:
                charsleft = (charsleft << 6) | UB64(ch)
                bitsleft += 6
                i += 1
##                /* p, charsleft, bitsleft, surrogate = */ DECODE(p, charsleft, bitsleft, surrogate);
        elif ( ch == '+' ):
            startinpos = i
            i += 1
            if (i<size and s[i] == '-'):
                i += 1
                p +=  '+'
            else:
                inShift = 1
                bitsleft = 0
                
        elif (SPECIAL(ch, 0, 0)):
            i += 1
            raise UnicodeDecodeError, "unexpected special character"
        else:
            p +=  ch 
            i += 1

    if (inShift) :
        #XXX This aint right
        endinpos = size
        raise UnicodeDecodeError, "unterminated shift sequence"
        
    return p

def PyUnicode_EncodeUTF7(s, size, encodeSetO, encodeWhiteSpace, errors):

#    /* It might be possible to tighten this worst case */
    inShift = False
    i = 0
    bitsleft = 0
    charsleft = 0
    out = []
    for ch in s:
        if (not inShift) :
            if (ch == '+'):
                out +=  '+'
                out +=  '-'
            elif (SPECIAL(ch, encodeSetO, encodeWhiteSpace)):
                charsleft = ord(ch)
                bitsleft = 16
                out += '+'
                p, bitsleft = ENCODE( charsleft, bitsleft)
                out += p
                inShift = bitsleft > 0
            else:
                out += chr(ord(ch))
        else:
            if (not SPECIAL(ch, encodeSetO, encodeWhiteSpace)):
                out += B64((charsleft) << (6-bitsleft))
                charsleft = 0
                bitsleft = 0
##                /* Characters not in the BASE64 set implicitly unshift the sequence
##                   so no '-' is required, except if the character is itself a '-' */
                if (B64CHAR(ch) or ch == '-'):
                    out += '-'
                inShift = False
                out += chr(ord(ch))
            else:
                bitsleft += 16
                charsleft = (((charsleft) << 16) | ord(ch))
                p, bitsleft =  ENCODE(charsleft, bitsleft)
                out += p
##                /* If the next character is special then we dont' need to terminate
##                   the shift sequence. If the next character is not a BASE64 character
##                   or '-' then the shift sequence will be terminated implicitly and we
##                   don't have to insert a '-'. */

                if (bitsleft == 0):
                    if (i + 1 < size):
                        ch2 = s[i+1]

                        if (SPECIAL(ch2, encodeSetO, encodeWhiteSpace)):
                            pass
                        elif (B64CHAR(ch2) or ch2 == '-'):
                            out +=  '-'
                            inShift = False
                        else:
                            inShift = False
                    else:
                        out +=  '-'
                        inShift = False
        i += 1
            
    if (bitsleft):
        out += B64(charsleft << (6-bitsleft) ) 
        out +=  '-'

    return out

unicode_empty = u''

def unicodeescape_string(s, size, quotes):

    p = []
    if (quotes) :
        p += 'u'
        if (s.find('\'') != -1 and s.find('"') == -1):
            p += '"' 
        else:
            p += '\''
    pos = 0
    while (pos < size):
        ch = s[pos]
        #/* Escape quotes */
        if (quotes and (ch == p[1] or ch == '\\')):
            p += '\\'
            p += chr(ord(ch))
            pos += 1
            continue

#ifdef Py_UNICODE_WIDE
        #/* Map 21-bit characters to '\U00xxxxxx' */
        elif (ord(ch) >= 0x10000):
            p += '\\'
            p += 'U'
            p += '%08x' % ord(ch)
            pos += 1
            continue        
#endif
        #/* Map UTF-16 surrogate pairs to Unicode \UXXXXXXXX escapes */
        elif (ord(ch) >= 0xD800 and ord(ch) < 0xDC00):
            pos += 1
            ch2 = s[pos]
            
            if (ord(ch2) >= 0xDC00 and ord(ch2) <= 0xDFFF):
                ucs = (((ord(ch) & 0x03FF) << 10) | (ord(ch2) & 0x03FF)) + 0x00010000
                p += '\\'
                p += 'U'
                p += '%08x' % ucs
                pos += 1
                continue
           
            #/* Fall through: isolated surrogates are copied as-is */
            pos -= 1
            
        #/* Map 16-bit characters to '\uxxxx' */
        if (ord(ch) >= 256):
            p += '\\'
            p += 'u'
            p += '%04x' % ord(ch)
            
        #/* Map special whitespace to '\t', \n', '\r' */
        elif (ch == '\t'):
            p += '\\'
            p += 't'
        
        elif (ch == '\n'):
            p += '\\'
            p += 'n'

        elif (ch == '\r'):
            p += '\\'
            p += 'r'

        #/* Map non-printable US ASCII to '\xhh' */
        elif (ch < ' ' or ch >= 0x7F) :
            p += '\\'
            p += 'x'
            p += '%02x' % ord(ch)
        #/* Copy everything else as-is */
        else:
            p += chr(ord(ch))
        pos += 1
    if (quotes):
        p += p[1]
    return p


def PyUnicode_DecodeMBCS(s, size, errors):
    pass

def PyUnicode_EncodeMBCS(p, size, errors):
    pass

def unicode_call_errorhandler(errors,  encoding, 
                reason, input, startinpos, endinpos, decode=True):
    
    import _codecs
    errorHandler = _codecs.lookup_error(errors)
    if decode:
        exceptionObject = UnicodeDecodeError(encoding, input, startinpos, endinpos, reason)
    else:
        exceptionObject = UnicodeEncodeError(encoding, input, startinpos, endinpos, reason)
    res = errorHandler(exceptionObject)
    if isinstance(res, tuple) and isinstance(res[0], unicode) and isinstance(res[1], int):
        newpos = res[1]
        if (newpos < 0):
            newpos = len(input) + newpos
        if newpos < 0 or newpos > len(input):
            raise IndexError( "position %d from error handler out of bounds" % newpos)
        return res[0], newpos
    else:
        raise TypeError("encoding error handler must return (unicode, int) tuple, not %s" % repr(res))



hexdigits = [hex(i)[-1] for i in range(16)]+[hex(i)[-1].upper() for i in range(10, 16)]

def hexescape(s, pos, digits, message, errors):
    chr = 0
    p = []
    if (pos+digits>len(s)):
        message = "end of string in escape sequence"
        x = unicode_call_errorhandler(errors, "unicodeescape", message, s, pos-2, len(s))
        p += x[0]
        pos = x[1]
    else:
        try:
            chr = int(s[pos:pos+digits], 16)
        except ValueError:
            endinpos = pos
            while s[endinpos] in hexdigits: 
                endinpos += 1
            x = unicode_call_errorhandler(errors, "unicodeescape", message, s, pos-2,
                        endinpos+1)
            p += x[0]
            pos = x[1]
        #/* when we get here, chr is a 32-bit unicode character */
        else:
            if chr <= sys.maxunicode:
                p += unichr(chr)
                pos += digits
            
            elif (chr <= 0x10ffff):
                chr -= 0x10000L
                p += unichr(0xD800 + (chr >> 10))
                p += unichr(0xDC00 +  (chr & 0x03FF))
                pos += digits
            else:
                message = "illegal Unicode character"
                x = unicode_call_errorhandler(errors, "unicodeescape", message, s, pos-2,
                        pos+1)
                p += x[0]
                pos = x[1]
    res = p
    return res, pos

def PyUnicode_DecodeUnicodeEscape(s, size, errors):

    if (size == 0):
        return u''
    
    p = []
    pos = 0
    while (pos < size): 
##        /* Non-escape characters are interpreted as Unicode ordinals */
        if (s[pos] != '\\') :
            p += unichr(ord(s[pos]))
            pos += 1
            continue
##        /* \ - Escapes */
        else:
            pos += 1
            if pos >= len(s):
                errmessage = "\\ at end of string"
                unicode_call_errorhandler(errors, "unicodeescape", errmessage, s, pos-1, size)
            ch = s[pos]
            pos += 1
    ##        /* \x escapes */
            if ch == '\\'  : p += u'\\'
            elif ch == '\'': p += u'\''
            elif ch == '\"': p += u'\"' 
            elif ch == 'b' : p += u'\b' 
            elif ch == 'f' : p += u'\014' #/* FF */
            elif ch == 't' : p += u'\t' 
            elif ch == 'n' : p += u'\n'
            elif ch == 'r' : p += u'\r' 
            elif ch == 'v': p += u'\013' #break; /* VT */
            elif ch == 'a': p += u'\007' # break; /* BEL, not classic C */
            elif '0' <= ch <= '7':
                x = ord(ch) - ord('0')
                if pos < size:
                    ch = s[pos]
                    if '0' <= ch <= '7':
                        pos += 1
                        x = (x<<3) + ord(ch) - ord('0')
                        if pos < size:
                            ch = s[pos]
                            if '0' <= ch <= '7':
                                pos += 1
                                x = (x<<3) + ord(ch) - ord('0')
                p += unichr(x)
    ##        /* hex escapes */
    ##        /* \xXX */
            elif ch == 'x':
                digits = 2
                message = "truncated \\xXX escape"
                x = hexescape(s, pos, digits, message, errors)
                p += x[0]
                pos = x[1]
    
         #   /* \uXXXX */
            elif ch == 'u':
                digits = 4
                message = "truncated \\uXXXX escape"
                x = hexescape(s, pos, digits, message, errors)
                p += x[0]
                pos = x[1]
    
          #  /* \UXXXXXXXX */
            elif ch == 'U':
                digits = 8
                message = "truncated \\UXXXXXXXX escape"
                x = hexescape(s, pos, digits, message, errors)
                p += x[0]
                pos = x[1]
##        /* \N{name} */
            elif ch == 'N':
                message = "malformed \\N character escape"
                #pos += 1
                look = pos
                try:
                    import unicodedata
                except ImportError:
                    message = "\\N escapes not supported (can't load unicodedata module)"
                    unicode_call_errorhandler(errors, "unicodeescape", message, s, pos-1, size)
                if look < size and s[look] == '{':
                    #/* look for the closing brace */
                    while (look < size and s[look] != '}'):
                        look += 1
                    if (look > pos+1 and look < size and s[look] == '}'):
                        #/* found a name.  look it up in the unicode database */
                        message = "unknown Unicode character name"
                        st = s[pos+1:look]
                        try:
                            chr = unicodedata.lookup("%s" % st)
                        except KeyError, e:
                            x = unicode_call_errorhandler(errors, "unicodeescape", message, s, pos-1, look+1)
                        else:
                            x = chr, look + 1 
                        p += x[0]
                        pos = x[1]
                    else:        
                        x = unicode_call_errorhandler(errors, "unicodeescape", message, s, pos-1, look+1)
                else:        
                    x = unicode_call_errorhandler(errors, "unicodeescape", message, s, pos-1, look+1)
            else:
                p += '\\'
                p += ch
    return p

def PyUnicode_EncodeRawUnicodeEscape(s, size):
    
    if (size == 0):
        return ''

    p = []
    for ch in s:
#       /* Map 32-bit characters to '\Uxxxxxxxx' */
        if (ord(ch) >= 0x10000):
            p += '\\'
            p += 'U'
            p += '%08x' % (ord(ch))
        elif (ord(ch) >= 256) :
#       /* Map 16-bit characters to '\uxxxx' */
            p += '\\'
            p += 'u'
            p += '%04x' % (ord(ch))
#       /* Copy everything else as-is */
        else:
            p += chr(ord(ch))
    
    #p += '\0'
    return p

def charmapencode_output(c, mapping):

    rep = mapping[c]
    if isinstance(rep, int) or isinstance(rep, long):
        if rep < 256:
            return chr(rep)
        else:
            raise TypeError("character mapping must be in range(256)")
    elif isinstance(rep, str):
        return rep
    elif rep == None:
        raise KeyError("character maps to <undefined>")
    else:
        raise TypeError("character mapping must return integer, None or str")

def PyUnicode_EncodeCharmap(p, size, mapping='latin-1', errors='strict'):

##    /* the following variable is used for caching string comparisons
##     * -1=not initialized, 0=unknown, 1=strict, 2=replace,
##     * 3=ignore, 4=xmlcharrefreplace */

#    /* Default to Latin-1 */
    if mapping == 'latin-1':
        import _codecs
        return _codecs.latin_1_encode(p, size, errors)
    if (size == 0):
        return ''
    inpos = 0
    res = []
    while (inpos<size):
        #/* try to encode it */
        try:
            x = charmapencode_output(ord(p[inpos]), mapping)
            res += [x]
        except KeyError:
            x = unicode_call_errorhandler(errors, "charmap",
            "character maps to <undefined>", p, inpos, inpos+1, False)
            try:
                res += [charmapencode_output(ord(y), mapping) for y in x[0]]
            except KeyError:
                raise UnicodeEncodeError("charmap", p, inpos, inpos+1,
                                        "character maps to <undefined>")
        inpos += 1
    return res

def PyUnicode_DecodeCharmap(s, size, mapping, errors):

##    /* Default to Latin-1 */
    if (mapping == None):
        import _codecs
        return _codecs.latin_1_decode(s, size, errors)

    if (size == 0):
        return u''
    p = []
    inpos = 0
    while (inpos< len(s)):
        
        #/* Get mapping (char ordinal -> integer, Unicode char or None) */
        ch = s[inpos]
        try:
            x = mapping[ord(ch)]
            if isinstance(x, int):
                if x < 65536:
                    p += unichr(x)
                else:
                    raise TypeError("character mapping must be in range(65536)")
            elif isinstance(x, unicode):
                p += x
            elif not x:
                raise KeyError
            else:
                raise TypeError
        except KeyError:
            x = unicode_call_errorhandler(errors, "charmap",
                "character maps to <undefined>", s, inpos, inpos+1)
            p += x[0]
        inpos += 1
    return p

def PyUnicode_DecodeRawUnicodeEscape(s, size, errors):

    if (size == 0):
        return u''
    pos = 0
    p = []
    while (pos < len(s)):
        ch = s[pos]
    #/* Non-escape characters are interpreted as Unicode ordinals */
        if (ch != '\\'):
            p += unichr(ord(ch))
            pos += 1
            continue        
        startinpos = pos
##      /* \u-escapes are only interpreted iff the number of leading
##         backslashes is odd */
        bs = pos
        while pos < size:
            if (s[pos] != '\\'):
                break
            p += unichr(ord(s[pos]))
            pos += 1
    
        if (((pos - bs) & 1) == 0 or
            pos >= size or
            (s[pos] != 'u' and s[pos] != 'U')) :
            p += unichr(ord(s[pos]))
            pos += 1
            continue
        
        p.pop(-1)
        if s[pos] == 'u':
            count = 4 
        else: 
            count = 8
        pos += 1

        #/* \uXXXX with 4 hex digits, \Uxxxxxxxx with 8 */
        x = 0
        try:
            x = int(s[pos:pos+count], 16)
        except ValueError:
            res = unicode_call_errorhandler(
                    errors, "rawunicodeescape", "truncated \\uXXXX",
                    s, size, pos, pos+count)
            p += res[0]
            pos = res[1]
        else:
    #ifndef Py_UNICODE_WIDE
            if sys.maxunicode > 0xffff:
                if (x > sys.maxunicode):
                    res = unicode_call_errorhandler(
                        errors, "rawunicodeescape", "\\Uxxxxxxxx out of range",
                        s, size, pos, pos+1)
                    pos = res[1]
                    p += res[0]
                else:
                    p += unichr(x)
                    pos += count
            else:
                if (x > 0x10000):
                    res = unicode_call_errorhandler(
                        errors, "rawunicodeescape", "\\Uxxxxxxxx out of range",
                        s, size, pos, pos+1)
                    pos = res[1]
                    p += res[0]

    #endif
                else:
                    p += unichr(x)
                    pos += count

    return p
