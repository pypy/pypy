
## indicate whether a UTF-7 character is special i.e. cannot be directly
##       encoded:
##	   0 - not special
##	   1 - special
##	   2 - whitespace (optional)
##	   3 - RFC2152 Set O (optional)
    
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
unicode_latin1=[]

codec_error_registry = {}
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
    
for i in range(256):
    unicode_latin1.append(None)
    
def PyUnicode_Check(op):
    return type(op) == unicode
def PyUnicode_CheckExact(op):
    return (type(op) == unicode)


def PyUnicode_GET_SIZE(op):
        return len(unicode(op))
def PyUnicode_GET_DATA_SIZE(op):
        return len(unicode(op)) * len(u' ')
def PyUnicode_AS_UNICODE(op):
        unicode(op)
def PyUnicode_AS_DATA(op):
        buffer(unicode(op)) #XXX This is a read only buffer

def SPECIAL(c, encodeO, encodeWS):
    c = ord(c)
    return (c>127 or utf7_special[c] == 1) or \
            (encodeWS and (utf7_special[(c)] == 2)) or \
            (encodeO and (utf7_special[(c)] == 3))
def B64(n):
    return ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[(n) & 0x3f])
def B64CHAR(c):
    return (isalnum(c) or (c) == '+' or (c) == '/')
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

def ENCODE(out, ch, bits) :
    while (bits >= 6):
        out.append( B64(ch >> (bits-6)))
        bits -= 6; 
    return ''.join(out),ch,bits

def DECODE(out, ch, bits, surrogate):
    while (bits >= 16):
        outCh = unicode (chr((ord(ch) >> (bits-16)) & 0xffff))
        bits -= 16
        if (surrogate):
            ##            We have already generated an error for the high surrogate
            ##            so let's not bother seeing if the low surrogate is correct or not 
			surrogate = 0
        elif (0xDC00 <= outCh and outCh <= 0xDFFF):
##             This is a surrogate pair. Unfortunately we can't represent 
##               it in a 16-bit character 
            surrogate = 1
            raise UnicodeDecodeError,"code pairs are not supported"
        else:
			out.append( outCh )
    return ''.join(out),ch,bits,surrogate

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
                p, charsleft, bitsleft, surrogate =  DECODE(p, charsleft, bitsleft, surrogate);
                if (bitsleft >= 6):
##                    /* The shift sequence has a partial character in it. If
##                       bitsleft < 6 then we could just classify it as padding
##                       but that is not the case here */

                    raise UnicodeDecodeError, "partial character in shift sequence"
##                /* According to RFC2152 the remaining bits should be zero. We
##                   choose to signal an error/insert a replacement character
##                   here so indicate the potential of a misencoded character. */

##                /* On x86, a << b == a << (b%32) so make sure that bitsleft != 0 */
                if (bitsleft and (charsleft << (sizeof(charsleft) * 8 - bitsleft))):
                    raise UnicodeDecodeError, "non-zero padding bits in shift sequence"
                if (ch == '-') :
                    if ((i < size) and (s[i] == '-')) :
                        p.append( '-')
                        inShift = 1
                    
                elif SPECIAL(ch,0,0) :
                    raise  UnicodeDecodeError,"unexpected special character"
	                
                else:  
                    p.append( ch )
            else:
                charsleft = (charsleft << 6) | UB64(ch)
                bitsleft += 6
                i+=1
##                /* p, charsleft, bitsleft, surrogate = */ DECODE(p, charsleft, bitsleft, surrogate);
        elif ( ch == '+' ):
            startinpos = i
            i+=1
            if (i<size and s[i] == '-'):
                i+=1
                p.append( '+')
            else:
                inShift = 1
                bitsleft = 0
                
        elif (SPECIAL(ch,0,0)):
            i+=1
            raise UnicodeDecodeError,"unexpected special character"
        else:
            p.append( ch )
            i+=1

    if (inShift) :
        outpos = p-PyUnicode_AS_UNICODE(unicode);
        endinpos = size;
        raise UnicodeDecodeError, "unterminated shift sequence"
        
    return unicode(''.join(p))

def PyUnicode_EncodeUTF7(s, size, encodeSetO, encodeWhiteSpace, errors):

#    /* It might be possible to tighten this worst case */
    inShift = 0
    i = 0
    bitsleft = 0
    charsleft = 0
    out = []
    for ch in s:
        if (not inShift) :
            if (ch == '+'):
                out.append( '+')
                out.append( '-')
            elif (SPECIAL(ch, encodeSetO, encodeWhiteSpace)):
                charsleft = ch
                bitsleft = 16
                out.append('+')
                out, charsleft, bitsleft = ENCODE(out, charsleft, bitsleft)
                inShift = bitsleft > 0
            else:
                out.append(ch)
        else:
            if (not SPECIAL(ch, encodeSetO, encodeWhiteSpace)):
                out.append(B64(charsleft << (6-bitsleft)))
                charsleft = 0
                bitsleft = 0
##                /* Characters not in the BASE64 set implicitly unshift the sequence
##                   so no '-' is required, except if the character is itself a '-' */
                if (B64CHAR(ch) or ch == '-'):
                    out.append('-')
                inShift = 0
                out.append(ch)
            else:
                bitsleft += 16
                charsleft = (charsleft << 16) | ch
                out, charsleft, bitsleft =  ENCODE(out, charsleft, bitsleft)

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
                            out.append( '-')
                            inShift = 0
                        else:
                            inShift = 0
                    else:
                        out.append( '-')
                        inShift = 0
        i+=1
            
    if (bitsleft):
        out.append(B64(charsleft << (6-bitsleft) ))
        out.append( '-')

    return ''.join(out)

def PyUnicode_FromOrdinal(ordinal):
    
    if (ordinal < 0 or ordinal > 0x10ffff):
        raise ValueError, "unichr() arg not in range(0x110000) (wide Python build)"
	
##    if (ordinal < 0 or ordinal > 0xffff):
##        raise ValueError, "unichr() arg not in range(0x1000) (narrow Python build)"
	
    s = unichr(ordinal)
    return s,1

def PyUnicode_FromObject(obj):

##    /* XXX Perhaps we should make this API an alias of
##           PyObject_Unicode() instead ?! */
    if (PyUnicode_CheckExact(obj)):
        return obj
    
    if (PyUnicode_Check(obj)):
##	/* For a Unicode subtype that's not a Unicode object,
##	   return a true Unicode object with the same data. */
        return PyUnicode_FromUnicode(PyUnicode_AS_UNICODE(obj),PyUnicode_GET_SIZE(obj))
    return PyUnicode_FromEncodedObject(obj, None, "strict")

unicode_empty=u''

def PyUnicode_FromUnicode(u, size):

##    /* If the Unicode data is known at construction time, we can apply
##       some optimizations which share commonly used objects. */
    if (u):

##	/* Optimization for empty strings */
    	if (size == 0 and unicode_empty != None) :
    	    return unicode_empty
    
    ##	/* Single character Unicode objects in the Latin-1 range are
    ##	   shared when using this constructor */
    	if (size == 1 and ord(u) < 256) :
            result = unicode_latin1[ord(u)]
    	    if (not result):
                result = unicode(u)
                unicode_latin1[ord(u)] = result
    		if (not result):
    		    return None
    	    return result
        return unicode(u)
    
def PyUnicode_Decode(s,size,encoding,errors):

    if (encoding == None):
        encoding = PyUnicode_GetDefaultEncoding()

##    /* Shortcuts for common default encodings */
    decoder = encodings.get(encoding,None)
    if decoder:
        return decoder(s,encoding,errors)
##    /* Decode via the codec registry */
    buf = buffer(s)
    result = PyCodec_Decode(buf, encoding, errors);
    if (not PyUnicode_Check(result)):
        raise UnicodeDecodeError, "decoder did not return an unicode object (type=%.400s)"%type(result)
    return result

def PyUnicode_FromEncodedObject(obj, encoding,errors):
    
    s = str(obj)
    v = PyUnicode_Decode(s, len(s), encoding, errors)
    return v

def PyUnicode_DecodeASCII(s, size, errors):

#    /* ASCII is equivalent to the first 128 ordinals in Unicode. */
    if (size == 1 and ord(s) < 128) :
        return PyUnicode_FromUnicode(unicode(s), 1)
    if (size == 0):
        return unicode('')
    p = []
    for c in s:
        if ord(c) < 128:
            p.append(c)
        else:
            UnicodeDecodeError("ordinal not in range(128)",s.index(c))
    return ''.join(p)

def PyUnicode_EncodeASCII(p,size,errors):

    return u''.join(unicode_encode_ucs1(p, size, errors, 128))

def PyUnicode_AsASCIIString(unistr):

    if not type(unistr) == unicode:
        raise BadArgumnentError
    return PyUnicode_EncodeASCII(PyUnicode_AS_UNICODE(unistr),
				 len(unicode),
				None)

##def PyUnicode_DecodeUTF16Stateful(s,size,errors,byteorder,consumed):
##
##    bo = 0;       /* assume native ordering by default */
##    errmsg = "";
##    /* Offsets from q for retrieving byte pairs in the right order. */
###ifdef BYTEORDER_IS_LITTLE_ENDIAN
##    int ihi = 1, ilo = 0;
###else
##    int ihi = 0, ilo = 1;
###endif
##    PyObject *errorHandler = NULL;
##    PyObject *exc = NULL;
##
##    /* Note: size will always be longer than the resulting Unicode
##       character count */
##    unicode = _PyUnicode_New(size);
##    if (!unicode)
##        return NULL;
##    if (size == 0)
##        return (PyObject *)unicode;
##
##    /* Unpack UTF-16 encoded data */
##    p = unicode->str;
##    q = (unsigned char *)s;
##    e = q + size;
##
##    if (byteorder)
##        bo = *byteorder;
##
##    /* Check for BOM marks (U+FEFF) in the input and adjust current
##       byte order setting accordingly. In native mode, the leading BOM
##       mark is skipped, in all other modes, it is copied to the output
##       stream as-is (giving a ZWNBSP character). */
##    if (bo == 0) {
##        if (size >= 2) {
##            const Py_UNICODE bom = (q[ihi] << 8) | q[ilo];
###ifdef BYTEORDER_IS_LITTLE_ENDIAN
##	    if (bom == 0xFEFF) {
##		q += 2;
##		bo = -1;
##	    }
##	    else if (bom == 0xFFFE) {
##		q += 2;
##		bo = 1;
##	    }
###else
##	    if (bom == 0xFEFF) {
##		q += 2;
##		bo = 1;
##	    }
##	    else if (bom == 0xFFFE) {
##		q += 2;
##		bo = -1;
##	    }
###endif
##	}
##    }
##
##    if (bo == -1) {
##        /* force LE */
##        ihi = 1;
##        ilo = 0;
##    }
##    else if (bo == 1) {
##        /* force BE */
##        ihi = 0;
##        ilo = 1;
##    }
##
##    while (q < e) {
##	Py_UNICODE ch;
##	/* remaining bytes at the end? (size should be even) */
##	if (e-q<2) {
##	    if (consumed)
##		break;
##	    errmsg = "truncated data";
##	    startinpos = ((const char *)q)-starts;
##	    endinpos = ((const char *)e)-starts;
##	    goto utf16Error;
##	    /* The remaining input chars are ignored if the callback
##	       chooses to skip the input */
##	}
##	ch = (q[ihi] << 8) | q[ilo];
##
##	q += 2;
##
##	if (ch < 0xD800 || ch > 0xDFFF) {
##	    *p++ = ch;
##	    continue;
##	}
##
##	/* UTF-16 code pair: */
##	if (q >= e) {
##	    errmsg = "unexpected end of data";
##	    startinpos = (((const char *)q)-2)-starts;
##	    endinpos = ((const char *)e)-starts;
##	    goto utf16Error;
##	}
##	if (0xD800 <= ch && ch <= 0xDBFF) {
##	    Py_UNICODE ch2 = (q[ihi] << 8) | q[ilo];
##	    q += 2;
##	    if (0xDC00 <= ch2 && ch2 <= 0xDFFF) {
###ifndef Py_UNICODE_WIDE
##		*p++ = ch;
##		*p++ = ch2;
###else
##		*p++ = (((ch & 0x3FF)<<10) | (ch2 & 0x3FF)) + 0x10000;
###endif
##		continue;
##	    }
##	    else {
##                errmsg = "illegal UTF-16 surrogate";
##		startinpos = (((const char *)q)-4)-starts;
##		endinpos = startinpos+2;
##		goto utf16Error;
##	    }
##
##	}
##	errmsg = "illegal encoding";
##	startinpos = (((const char *)q)-2)-starts;
##	endinpos = startinpos+2;
##	/* Fall through to report the error */
##
##    utf16Error:
##	outpos = p-PyUnicode_AS_UNICODE(unicode);
##	if (unicode_decode_call_errorhandler(
##	         errors, &errorHandler,
##	         "utf16", errmsg,
##	         starts, size, &startinpos, &endinpos, &exc, (const char **)&q,
##	         (PyObject **)&unicode, &outpos, &p))
##	    goto onError;
##    }
##
##    if (byteorder)
##        *byteorder = bo;
##
##    if (consumed)
##	*consumed = (const char *)q-starts;
##
##    /* Adjust length */
##    if (_PyUnicode_Resize(&unicode, p - unicode->str) < 0)
##        goto onError;
##
##    Py_XDECREF(errorHandler);
##    Py_XDECREF(exc);
##    return (PyObject *)unicode;
##
##onError:
##    Py_DECREF(unicode);
##    Py_XDECREF(errorHandler);
##    Py_XDECREF(exc);
##    return NULL;
##}

def PyUnicode_EncodeUTF16(s,size,errors,byteorder='little'):

#    /* Offsets from p for storing byte pairs in the right order. */
###ifdef BYTEORDER_IS_LITTLE_ENDIAN
##    int ihi = 1, ilo = 0;
###else
##    int ihi = 0, ilo = 1;
###endif

    def STORECHAR(CH,byteorder):
        hi = chr(((CH) >> 8) & 0xff)
        lo = chr((CH) & 0xff)
        if byteorder == 'little':
            return [lo,hi]
        else:
            return [hi,lo]
        
    p = []
    import sys
    bom = sys.byteorder
    if (byteorder == 0):
        import sys
        bom = sys.byteorder
        p.extend(STORECHAR(0xFEFF,bom))
        
    if (size == 0):
        return ""

    if (byteorder == -1):
        bom = 'little'
    elif (byteorder == 1):
        bom = 'big'

    
    for c in s:
        ch = ord(c)
        ch2 = 0
        if (ch >= 0x10000) :
            ch2 = 0xDC00 | ((ch-0x10000) & 0x3FF)
            ch  = 0xD800 | ((ch-0x10000) >> 10)

        p.extend(STORECHAR(ch,bom))
        if (ch2):
            p.extend(STORECHAR(ch2,bom))

    return ''.join(p)


def PyUnicode_DecodeMBCS(s, size, errors):
    pass
##{
##    PyUnicodeObject *v;
##    Py_UNICODE *p;
##
##    /* First get the size of the result */
##    DWORD usize = MultiByteToWideChar(CP_ACP, 0, s, size, NULL, 0);
##    if (size > 0 && usize==0)
##        return PyErr_SetFromWindowsErrWithFilename(0, NULL);
##
##    v = _PyUnicode_New(usize);
##    if (v == NULL)
##        return NULL;
##    if (usize == 0)
##	return (PyObject *)v;
##    p = PyUnicode_AS_UNICODE(v);
##    if (0 == MultiByteToWideChar(CP_ACP, 0, s, size, p, usize)) {
##        Py_DECREF(v);
##        return PyErr_SetFromWindowsErrWithFilename(0, NULL);
##    }
##
##    return (PyObject *)v;
##}

##def PyUnicode_EncodeMBCS(p, size, errors):
##
####    /* If there are no characters, bail now! */
##    if (size==0)
##	    return ""
##    from ctypes import *
##    WideCharToMultiByte = windll.kernel32.WideCharToMultiByte
####    /* First get the size of the result */
##    mbcssize = WideCharToMultiByte(CP_ACP, 0, p, size, s, 0, None, None);
##    if (mbcssize==0)
##        raise UnicodeEncodeError, "Windows cannot decode the string %s" %p
### More error handling required (check windows errors and such)
##    
###    /* Do the conversion */
####    s = ' '*mbcssize
####    if (0 == WideCharToMultiByte(CP_ACP, 0, p, size, s, mbcssize, NULL, NULL)):
####        raise UnicodeEncodeError, "Windows cannot decode the string %s" %p
##    return s
def unicode_decode_call_errorhandler(errors, errorHandler, encoding, 
                reason, input, insize, startinpos, endinpos, exceptionObject):

    if not errorHandler:
        errorHandler = lookup_error(errors)

    if not exceptionObject:
        exceptionObject = UnicodeDecodeError(encoding, input, insize, startinpos, endinpos, reason)
    else:
	    exceptionObject.start = startinpos
	    exceptionObject.ens = endinpos
	    exceptionObject.resason = reason

    res,newpos = errorHandler(exceptionObject)
    if (newpos<0):
        newpos = insize+newpos;
    if newpos<0 or newpos>insize:
        raise IndexError( "position %d from error handler out of bounds", newpos)
	return res,newpos

def PyUnicode_DecodeUTF8(s, size, errors):

    return PyUnicode_DecodeUTF8Stateful(s, size, errors, None);

##    /* Map UTF-8 encoded prefix byte to sequence length.  zero means
##       illegal prefix.  see RFC 2279 for details */
utf8_code_length = [
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 0, 0
]

def PyUnicode_DecodeUTF8Stateful(s,size,errors,consumed):
    
##{
##    const char *starts = s;
##    int n;
##    int startinpos;
##    int endinpos;
##    int outpos;
##    const char *e;
##    PyUnicodeObject *unicode;
##    Py_UNICODE *p;
##    const char *errmsg = "";
##    PyObject *errorHandler = NULL;
##    PyObject *exc = NULL;
##
##    /* Note: size will always be longer than the resulting Unicode
##       character count */
##    unicode = _PyUnicode_New(size);
##    if (!unicode)
##        return NULL;
    if (size == 0):
        if (consumed):
            consumed = 0;
        return u''
    
    res = []
    for ch in s:
        if ord(ch) < 0x80:
            res.append(ch)
            continue
        
        n = utf8_code_length[ord(ch)]
        startinpos =  s.index(ch)
        if (startinpos + n > size):
            if (consumed):
                break
            else:
                errmsg = "unexpected end of data"
                endinpos = size
                p,outpos = unicode_decode_call_errorhandler(
                     errors, None,
                     "utf8", errmsg,
                     starts, size, startinpos, endinpos, s)
        if n == 0:
            errmsg = "unexpected code byte"
            endinpos = startinpos+1
        elif n == 1:
            errmsg = "internal error"
            endinpos = startinpos+1
        elif n == 2:
            if ((s[1] & 0xc0) != 0x80):
                errmsg = "invalid data"
                endinpos = startinpos+2
            c = ((ord(s[0]) & 0x1f) << 6) + (ord(s[1]) & 0x3f)
            if c<0x80:
                errmsg = "illegal encoding"
                endinpos = startinpos+2
                
            else:
                res.append(c)
                break
        elif n == 3:
            if ((s[1] & 0xc0) != 0x80 or
                    (s[2] & 0xc0) != 0x80):
                errmsg = "invalid data"
                endinpos = startinpos+3
            c = ((s[0] & 0x0f) << 12) + ((s[1] & 0x3f) << 6) + (s[2] & 0x3f)        
##		/* Note: UTF-8 encodings of surrogates are considered
##		   legal UTF-8 sequences;
##
##		   XXX For wide builds (UCS-4) we should probably try
##		       to recombine the surrogates into a single code
##		       unit.
##		*/
            if c < 0x8000:
                errmsg = "illegal encoding"
                endinpos = startinpos+3
            else:
                res.append(c)
##           p,outpos = unicode_decode_call_errorhandler(
##                     errors, None,
##                     "utf8", errmsg,
##                     starts, size, startinpos, endinpos, s)

##            ch = ((s[0] & 0x0f) << 12) + ((s[1] & 0x3f) << 6) + (s[2] & 0x3f);
##            if (ch < 0x0800) {
##                errmsg = "illegal encoding";
##		startinpos = s-starts;
##		endinpos = startinpos+3;
##		goto utf8Error;
##	    }
##	    else
##		*p++ = (Py_UNICODE)ch;
##            break;
##
##        case 4:
##            if ((s[1] & 0xc0) != 0x80 ||
##                (s[2] & 0xc0) != 0x80 ||
##                (s[3] & 0xc0) != 0x80) {
##                errmsg = "invalid data";
##		startinpos = s-starts;
##		endinpos = startinpos+4;
##		goto utf8Error;
##	    }
##            ch = ((s[0] & 0x7) << 18) + ((s[1] & 0x3f) << 12) +
##                 ((s[2] & 0x3f) << 6) + (s[3] & 0x3f);
##            /* validate and convert to UTF-16 */
##            if ((ch < 0x10000)        /* minimum value allowed for 4
##					 byte encoding */
##                || (ch > 0x10ffff))   /* maximum value allowed for
##					 UTF-16 */
##	    {
##                errmsg = "illegal encoding";
##		startinpos = s-starts;
##		endinpos = startinpos+4;
##		goto utf8Error;
##	    }
###ifdef Py_UNICODE_WIDE
##	    *p++ = (Py_UNICODE)ch;
###else
##            /*  compute and append the two surrogates: */
##
##            /*  translate from 10000..10FFFF to 0..FFFF */
##            ch -= 0x10000;
##
##            /*  high surrogate = top 10 bits added to D800 */
##            *p++ = (Py_UNICODE)(0xD800 + (ch >> 10));
##
##            /*  low surrogate = bottom 10 bits added to DC00 */
##            *p++ = (Py_UNICODE)(0xDC00 + (ch & 0x03FF));
###endif
##            break;
##
##        default:
##            /* Other sizes are only needed for UCS-4 */
##            errmsg = "unsupported Unicode code range";
##	    startinpos = s-starts;
##	    endinpos = startinpos+n;
##	    goto utf8Error;
##        }
##        s += n;
##	continue;
##
##    utf8Error:
##    outpos = p-PyUnicode_AS_UNICODE(unicode);
##    if (unicode_decode_call_errorhandler(
##	     errors, &errorHandler,
##	     "utf8", errmsg,
##	     starts, size, &startinpos, &endinpos, &exc, &s,
##	     (PyObject **)&unicode, &outpos, &p))
##	goto onError;
##    }
##    if (consumed)
##	*consumed = s-starts;
##
##    /* Adjust length */
##    if (_PyUnicode_Resize(&unicode, p - unicode->str) < 0)
##        goto onError;
##
##    Py_XDECREF(errorHandler);
##    Py_XDECREF(exc);
##    return (PyObject *)unicode;
##
##onError:
##    Py_XDECREF(errorHandler);
##    Py_XDECREF(exc);
##    Py_DECREF(unicode);
##    return NULL;
##}
##
##/* Allocation strategy:  if the string is short, convert into a stack buffer
##   and allocate exactly as much space needed at the end.  Else allocate the
##   maximum possible needed (4 result bytes per Unicode character), and return
##   the excess memory at the end.
##*/

def PyUnicode_EncodeUTF8(s,size,errors):

    assert(s != None)
    assert(size >= 0)
    p = []
    i = 0
    while i<size:
        ch = s[i]
        i+=1
        if (ord(ch) < 0x80):
##         /* Encode ASCII */
            p.append(ch)
        elif (ord(ch) < 0x0800) :
##            /* Encode Latin-1 */
            p.append(chr((0xc0 | (ch >> 6))))
            p.append(chr((0x80 | (ch & 0x3f))))
        else:
##            /* Encode UCS2 Unicode ordinals */
            if (ord(ch) < 0x10000):
##                /* Special case: check for high surrogate */
                if (0xD800 <=ord(ch) and ord(ch) <= 0xDBFF and i != size) :
                    ch2 = s[i]
##                    /* Check for low surrogate and combine the two to
##                       form a UCS4 value */
                    if (0xDC00 <= ch2 and ch2 <= 0xDFFF) :
                        ch = ((ch - 0xD800) << 10 | (ch2 - 0xDC00)) + 0x10000
                        i+=1
                        p.extend(encodeUCS4(ch))
                        continue
##                    /* Fall through: handles isolated high surrogates */
                p.append (chr((0xe0 | (ch >> 12))))
                p.append (chr((0x80 | ((ch >> 6) & 0x3f))))
                p.append (chr((0x80 | (ch & 0x3f))))
                continue
    return ''.join(p)

def encodeUCS4(ch):
##      /* Encode UCS4 Unicode ordinals */
    p=[]
    p.append (chr((0xf0 | (ch >> 18))))
    p.append (chr((0x80 | ((ch >> 12) & 0x3f))))
    p.append (chr((0x80 | ((ch >> 6) & 0x3f))))
    p.append (chr((0x80 | (ch & 0x3f))))
    return p

#/* --- Latin-1 Codec ------------------------------------------------------ */

def PyUnicode_DecodeLatin1(s, size, errors):
    pass
##{
##    PyUnicodeObject *v;
##    Py_UNICODE *p;
##
##    /* Latin-1 is equivalent to the first 256 ordinals in Unicode. */
##    if (size == 1) {
##	Py_UNICODE r = *(unsigned char*)s;
##	return PyUnicode_FromUnicode(&r, 1);
##    }
##
##    v = _PyUnicode_New(size);
##    if (v == NULL)
##	goto onError;
##    if (size == 0)
##	return (PyObject *)v;
##    p = PyUnicode_AS_UNICODE(v);
##    while (size-- > 0)
##	*p++ = (unsigned char)*s++;
##    return (PyObject *)v;
##
## onE rror:
##    Py_XDECREF(v);
##    return NULL;
##}


def unicode_encode_ucs1(p,size,errors,limit):
    
    if limit == 256:
        reason = "ordinal not in range(256)"
        encoding = "latin-1"
    else:
        reason = "ordinal not in range(128)"
        encoding = "ascii"
    
    if (size == 0):
        return ''
    res = []
    pos=0
    while pos < len(p):
    #for ch in p:
        ch = p[pos]
        if ord(ch) < limit:
            res.append(ch)
            pos += 1
        else:
            #/* startpos for collecting unencodable chars */
            collstart = p.index(ch)
            collend = p.index(ch)+1
            while collend < len(p) and ord(p[collend]) >= limit:
                collend += 1
            
            #uncollectable = [c for c in p if ord(c) >= limit]
            handler = lookup_error(errors)
            exc = UnicodeEncodeError(encoding,p,collstart,collend,reason)
            x = handler(exc)
            res.append(x[0])
            pos = x[1]
    
    return res #u''.join(res)

def PyUnicode_EncodeLatin1(p,size,errors):
    res=unicode_encode_ucs1(p, size, errors, 256)
    return u''.join(res)
def PyUnicode_EncodeRawUnicodeEscape(s,size):
    
    if (size == 0):
        return u''

    p = []
    for ch in s:
#	/* Map 32-bit characters to '\Uxxxxxxxx' */
        if (ord(ch) >= 0x10000):
            p.append('\\')
            p.append('U')
            p.append(hex(ord(ch)))
        elif (ord(ch) >= 256) :
#	/* Map 16-bit characters to '\uxxxx' */
            p.append('\\')
            p.append('u')
            p.append(hex(ord(ch)))
#	/* Copy everything else as-is */
        else:
            p.append(ch)
    
    p.append('\0')
    return ''.join(p)

def charmapencode_output(c,mapping,outobj,outpos):

    rep = mapping[c]

def PyUnicode_EncodeCharmap(p,size,mapping='latin-1',errors='strict'):

##    /* the following variable is used for caching string comparisons
##     * -1=not initialized, 0=unknown, 1=strict, 2=replace,
##     * 3=ignore, 4=xmlcharrefreplace */

#    /* Default to Latin-1 */
    if mapping == 'latin-1':
        return PyUnicode_EncodeLatin1(p, size, errors)
    if (size == 0):
        return ''
    inpos = 0
    res = []
    while (inpos<size):
	#/* try to encode it */
        try:
            x = mapping[ord(p[inpos])]
            res.append(unicode(x))
        except KeyError:
            handler = lookup_error(errors)
            x = handler(UnicodeEncodeError("charmap",p,inpos,inpos+1,
                "character maps to <undefined>"))
            res.append(mapping[ord(x[0])])
        #else:
	    #/* done with this character => adjust input position */
        inpos+=1
	
    
    return ''.join(res)


encodings =     {       "utf-8"     :   PyUnicode_DecodeUTF8,
                        "latin-1"   :   PyUnicode_DecodeLatin1,
                        "mbcs"      :   PyUnicode_DecodeMBCS,
                        "ascii"     :   PyUnicode_DecodeASCII,
                }        
