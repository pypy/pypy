from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import rstring
from rpython.rlib.rarithmetic import widen
from rpython.rlib import rstring, rutf8
from rpython.tool.sourcetools import func_renamer

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.unicodehelper import (
    wcharpsize2utf8, str_decode_utf_16_helper, str_decode_utf_32_helper,
    unicode_encode_decimal, utf8_encode_utf_16_helper, BYTEORDER,
    utf8_encode_utf_32_helper)
from pypy.objspace.std.unicodeobject import unicodedb
from pypy.module.cpyext.api import (
    CANNOT_FAIL, Py_ssize_t, build_type_checkers, cpython_api,
    bootstrap_function, CONST_STRING, INTP_real,
    CONST_WSTRING, Py_CLEANUP_SUPPORTED, slot_function, cts, parse_dir)
from pypy.module.cpyext.pyerrors import PyErr_BadArgument
from pypy.module.cpyext.pyobject import (
    PyObject, PyObjectP, decref, make_ref, from_ref, track_reference,
    make_typedescr, get_typedescr, as_pyobj)
from pypy.module.cpyext.bytesobject import PyBytes_Check, PyBytes_FromObject
from pypy.module._codecs.interp_codecs import (
    CodecState, latin_1_decode, utf_16_decode, utf_32_decode)
from pypy.objspace.std import unicodeobject
import sys

## See comment in bytesobject.py.

cts.parse_header(parse_dir / 'cpyext_unicodeobject.h')
PyUnicodeObject = cts.gettype('PyUnicodeObject*')
Py_UNICODE = cts.gettype('Py_UNICODE')
Py_UCS4 = cts.gettype('Py_UCS4')
INT_realP = lltype.Ptr(lltype.Array(rffi.INT_real, hints={'nolength': True}))

@bootstrap_function
def init_unicodeobject(space):
    make_typedescr(space.w_unicode.layout.typedef,
                   basestruct=PyUnicodeObject.TO,
                   attach=unicode_attach,
                   dealloc=unicode_dealloc,
                   realize=unicode_realize)

# Buffer for the default encoding (used by PyUnicode_GetDefaultEncoding)
DEFAULT_ENCODING_SIZE = 100
default_encoding = lltype.malloc(rffi.CCHARP.TO, DEFAULT_ENCODING_SIZE,
                                 flavor='raw', zero=True)

PyUnicode_Check, PyUnicode_CheckExact = build_type_checkers("Unicode")

MAX_UNICODE = 1114111
WCHAR_KIND = 0
_1BYTE_KIND = 1
_2BYTE_KIND = 2
_4BYTE_KIND = 4

kind_to_name = {
    0: 'WCHAR_KIND',
    1: '_1BYTE_KIND',
    2: '_2BYTE_KIND',
    4: '_4BYTE_KIND',
    }


def new_empty_unicode(space, length):
    """
    Allocate a PyUnicodeObject and its buffer, but without a corresponding
    interpreter object.  The buffer may be mutated, until unicode_realize() is
    called.  Refcount of the result is 1.
    """
    typedescr = get_typedescr(space.w_unicode.layout.typedef)
    py_obj = typedescr.allocate(space, space.w_unicode)

    buflen = length + 1
    set_wsize(py_obj, length)
    set_wbuffer(py_obj,
        lltype.malloc(
            rffi.CWCHARP.TO, buflen, flavor='raw', zero=True,
            add_memory_pressure=True))
    return py_obj

def unicode_attach(space, py_obj, w_obj, w_userdata=None):
    "Fills a newly allocated PyUnicodeObject with a unicode string"
    value = space.utf8_w(w_obj)
    length = space.len_w(w_obj)
    set_wsize(py_obj, length)
    set_wbuffer(py_obj, lltype.nullptr(rffi.CWCHARP.TO))
    _readify(space, py_obj, value)

def unicode_realize(space, py_obj):
    """
    Creates the unicode in the interpreter. The PyUnicodeObject buffer must not
    be modified after this call. Can raise in wcharpsize2utf8
    """
    lgt = get_wsize(py_obj)
    s_utf8 = wcharpsize2utf8(space, get_wbuffer(py_obj), lgt)
    w_type = from_ref(space, rffi.cast(PyObject, py_obj.c_ob_type))
    w_obj = space.allocate_instance(unicodeobject.W_UnicodeObject, w_type)
    w_obj.__init__(s_utf8, lgt)
    track_reference(space, py_obj, w_obj)
    return w_obj

@slot_function([PyObject], lltype.Void)
def unicode_dealloc(space, py_obj):
    if get_wbuffer(py_obj):
        lltype.free(get_wbuffer(py_obj), flavor="raw")
    if get_utf8(py_obj):
        lltype.free(get_utf8(py_obj), flavor="raw")
    from pypy.module.cpyext.object import _dealloc
    _dealloc(space, py_obj)

def get_len(py_obj):
    py_obj = cts.cast('PyASCIIObject*', py_obj)
    return py_obj.c_length

def set_len(py_obj, n):
    py_obj = cts.cast('PyASCIIObject*', py_obj)
    py_obj.c_length = n

def get_state(py_obj):
    py_obj = cts.cast('PyASCIIObject*', py_obj)
    return py_obj.c_state

def get_kind(py_obj):
    return rffi.getintfield(get_state(py_obj), 'c_kind')

def set_kind(py_obj, value):
    get_state(py_obj).c_kind = cts.cast('unsigned int', value)

def get_ascii(py_obj):
    return rffi.getintfield(get_state(py_obj), 'c_ascii')

def set_ascii(py_obj, value):
    get_state(py_obj).c_ascii = cts.cast('unsigned int', value)

def get_ready(py_obj):
    return rffi.getintfield(get_state(py_obj), 'c_ready')

def set_ready(py_obj, value):
    get_state(py_obj).c_ready = cts.cast('unsigned int', value)

def get_wbuffer(py_obj):
    py_obj = cts.cast('PyASCIIObject*', py_obj)
    return py_obj.c_wstr

def set_wbuffer(py_obj, wbuf):
    py_obj = cts.cast('PyASCIIObject*', py_obj)
    py_obj.c_wstr = wbuf

def get_utf8_len(py_obj):
    py_obj = cts.cast('PyCompactUnicodeObject*', py_obj)
    return py_obj.c_utf8_length

def set_utf8_len(py_obj, n):
    py_obj = cts.cast('PyCompactUnicodeObject*', py_obj)
    py_obj.c_utf8_length = n

def get_utf8(py_obj):
    py_obj = cts.cast('PyCompactUnicodeObject*', py_obj)
    return py_obj.c_utf8

def set_utf8(py_obj, buf):
    py_obj = cts.cast('PyCompactUnicodeObject*', py_obj)
    py_obj.c_utf8 = buf

def get_wsize(py_obj):
    py_obj = cts.cast('PyCompactUnicodeObject*', py_obj)
    return py_obj.c_wstr_length

def set_wsize(py_obj, value):
    py_obj = cts.cast('PyCompactUnicodeObject*', py_obj)
    py_obj.c_wstr_length = value

def get_data(py_obj):
    py_obj = cts.cast('PyUnicodeObject*', py_obj)
    return py_obj.c_data

def set_data(py_obj, p_data):
    py_obj = cts.cast('PyUnicodeObject*', py_obj)
    py_obj.c_data = p_data


@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISSPACE(space, ch):
    """Return 1 or 0 depending on whether ch is a whitespace character."""
    return unicodedb.isspace(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISALPHA(space, ch):
    """Return 1 or 0 depending on whether ch is an alphabetic character."""
    return unicodedb.isalpha(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISALNUM(space, ch):
    """Return 1 or 0 depending on whether ch is an alphanumeric character."""
    return unicodedb.isalnum(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISLINEBREAK(space, ch):
    """Return 1 or 0 depending on whether ch is a linebreak character."""
    return unicodedb.islinebreak(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISDECIMAL(space, ch):
    """Return 1 or 0 depending on whether ch is a decimal character."""
    return unicodedb.isdecimal(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISDIGIT(space, ch):
    """Return 1 or 0 depending on whether ch is a digit character."""
    return unicodedb.isdigit(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISNUMERIC(space, ch):
    """Return 1 or 0 depending on whether ch is a numeric character."""
    return unicodedb.isnumeric(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISLOWER(space, ch):
    """Return 1 or 0 depending on whether ch is a lowercase character."""
    return unicodedb.islower(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISUPPER(space, ch):
    """Return 1 or 0 depending on whether ch is an uppercase character."""
    return unicodedb.isupper(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISTITLE(space, ch):
    """Return 1 or 0 depending on whether ch is a titlecase character."""
    return unicodedb.istitle(ord(ch))

@cpython_api([Py_UNICODE], Py_UNICODE, error=CANNOT_FAIL)
def Py_UNICODE_TOLOWER(space, ch):
    """Return the character ch converted to lower case."""
    return unichr(unicodedb.tolower(ord(ch)))

@cpython_api([Py_UNICODE], Py_UNICODE, error=CANNOT_FAIL)
def Py_UNICODE_TOUPPER(space, ch):
    """Return the character ch converted to upper case."""
    return unichr(unicodedb.toupper(ord(ch)))

@cpython_api([Py_UNICODE], Py_UNICODE, error=CANNOT_FAIL)
def Py_UNICODE_TOTITLE(space, ch):
    """Return the character ch converted to title case."""
    return unichr(unicodedb.totitle(ord(ch)))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_TODECIMAL(space, ch):
    """Return the character ch converted to a decimal positive integer.  Return
    -1 if this is not possible.  This macro does not raise exceptions."""
    try:
        return unicodedb.decimal(ord(ch))
    except KeyError:
        return -1

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_TODIGIT(space, ch):
    """Return the character ch converted to a single digit integer. Return -1 if
    this is not possible.  This macro does not raise exceptions."""
    try:
        return unicodedb.digit(ord(ch))
    except KeyError:
        return -1

@cpython_api([Py_UNICODE], rffi.DOUBLE, error=CANNOT_FAIL)
def Py_UNICODE_TONUMERIC(space, ch):
    """Return the character ch converted to a double. Return -1.0 if this is not
    possible.  This macro does not raise exceptions."""
    try:
        return unicodedb.numeric(ord(ch))
    except KeyError:
        return -1.0

@cpython_api([], Py_UNICODE, error=CANNOT_FAIL)
def PyUnicode_GetMax(space):
    """Get the maximum ordinal for a Unicode character."""
    from rpython.rlib import runicode, rutf8
    return runicode.UNICHR(rutf8.MAXUNICODE)

@cts.decl("int _PyUnicode_Ready(PyObject *unicode)", error=-1)
def _PyUnicode_Ready(space, py_obj):
    # conversion from pyobj to space.w_unicode can fail,
    # so create the rpython object here and not in the api wrapper
    kind = get_kind(py_obj)
    if kind == WCHAR_KIND:
        w_obj = from_ref(space, rffi.cast(PyObject, py_obj))
    else:
        s = kind_to_name.get(kind, "INVALID")
        raise oefmt(space.w_ValueError,
            "converting %s PyUnicodeObject not supported yet", s)
    return _readify(space, py_obj, space.utf8_w(w_obj))

def _readify(space, py_obj, value):
    maxchar = 0
    for c in rutf8.Utf8StringIterator(value):
        if c > maxchar:
            maxchar = c
            if maxchar > MAX_UNICODE:
                raise oefmt(space.w_ValueError,
                    "Character U+%s is not in range [U+0000; U+10ffff]",
                    '%x' % maxchar)
    if maxchar < 256:
        ucs1_data = rffi.str2charp(value)
        set_data(py_obj, cts.cast('void*', ucs1_data))
        set_kind(py_obj, _1BYTE_KIND)
        set_len(py_obj, get_wsize(py_obj))
        if maxchar < 128:
            set_ascii(py_obj, 1)
            set_utf8(py_obj, cts.cast('char*', get_data(py_obj)))
            set_utf8_len(py_obj, get_wsize(py_obj))
        else:
            set_ascii(py_obj, 0)
            set_utf8(py_obj, cts.cast('char *', 0))
            set_utf8_len(py_obj, 0)
    elif maxchar < 65536:
        # XXX: assumes that sizeof(wchar_t) == 4
        ucs2_str = utf8_encode_utf_16_helper(
            value, 'strict',
            byteorder=BYTEORDER)
        ucs2_data = cts.cast('Py_UCS2 *', rffi.str2charp(ucs2_str))
        set_data(py_obj, cts.cast('void*', ucs2_data))
        set_len(py_obj, get_wsize(py_obj))
        set_kind(py_obj, _2BYTE_KIND)
        set_utf8(py_obj, cts.cast('char *', 0))
        set_utf8_len(py_obj, 0)
    else:
        # XXX: assumes that sizeof(wchar_t) == 4
        ucs4_str = utf8_encode_utf_32_helper(
            value, 'strict',
            byteorder=BYTEORDER)
        if not get_wbuffer(py_obj):
            # Copy unicode buffer
            wchar = cts.cast('wchar_t*', rffi.str2charp(ucs4_str))
            set_wbuffer(py_obj, wchar)
            set_wsize(py_obj, len(ucs4_str) // 4)
        ucs4_data = get_wbuffer(py_obj)
        set_data(py_obj, cts.cast('void*', ucs4_data))
        set_len(py_obj, get_wsize(py_obj))
        set_kind(py_obj, _4BYTE_KIND)
        set_utf8(py_obj, cts.cast('char *', 0))
        set_utf8_len(py_obj, 0)
    set_ready(py_obj, 1)
    return 0

@cts.decl("""PyObject* PyUnicode_FromKindAndData(
        int kind, const void *buffer, Py_ssize_t size)""")
def PyUnicode_FromKindAndData(space, kind, data, size):
    if size < 0:
        raise oefmt(space.w_ValueError, "size must be positive")
    data = cts.cast('char *', data)
    kind = widen(kind)
    if kind == _1BYTE_KIND:
        value = rffi.charpsize2str(data, size)
        w_res = latin_1_decode(space, value, w_final=space.w_False)
    elif kind == _2BYTE_KIND:
        value = rffi.charpsize2str(data, 2 * size)
        w_res = utf_16_decode(space, value, w_final=space.w_False)
    elif kind == _4BYTE_KIND:
        value = rffi.charpsize2str(data, 4 * size)
        w_res = utf_32_decode(space, value, w_final=space.w_False)
    else:
        raise oefmt(space.w_SystemError, "invalid kind")
    return space.unpackiterable(w_res)[0]

@cts.decl("Py_UNICODE * PyUnicode_AsUnicodeAndSize(PyObject *unicode, Py_ssize_t *size)")
def PyUnicode_AsUnicodeAndSize(space, ref, psize):
    """Return a read-only pointer to the Unicode object's internal Py_UNICODE
    buffer, NULL if unicode is not a Unicode object."""
    # Don't use PyUnicode_Check, it will realize the object :-(
    w_type = from_ref(space, rffi.cast(PyObject, ref.c_ob_type))
    if not space.issubtype_w(w_type, space.w_unicode):
        raise oefmt(space.w_TypeError, "expected unicode object")
    if not get_wbuffer(ref):
        # Copy unicode buffer
        w_unicode = from_ref(space, rffi.cast(PyObject, ref))
        u = space.utf8_w(w_unicode)
        lgt = space.len_w(w_unicode)
        set_wbuffer(ref, rffi.utf82wcharp(u, lgt))
        set_wsize(ref, lgt)
    if psize:
        psize[0] = get_wsize(ref)
    return get_wbuffer(ref)

@cts.decl("Py_UNICODE * PyUnicode_AsUnicode(PyObject *unicode)")
def PyUnicode_AsUnicode(space, ref):
    return PyUnicode_AsUnicodeAndSize(space, ref, cts.cast('Py_ssize_t *', 0))

@cts.decl("char * PyUnicode_AsUTF8AndSize(PyObject *unicode, Py_ssize_t *psize)")
def PyUnicode_AsUTF8AndSize(space, ref, psize):
    if not PyUnicode_Check(space, ref):
        PyErr_BadArgument(space)
    if not get_ready(ref):
        res = _PyUnicode_Ready(space, ref)

    if not get_utf8(ref):
        # Copy unicode buffer
        w_unicode = from_ref(space, ref)
        w_encoded = unicodeobject.encode_object(space, w_unicode, "utf-8",
                                                "strict")
        s = space.bytes_w(w_encoded)
        set_utf8(ref, rffi.str2charp(s))
        set_utf8_len(ref, len(s))
    if psize:
        psize[0] = get_utf8_len(ref)
    return get_utf8(ref)

@cts.decl("char * PyUnicode_AsUTF8(PyObject *unicode)")
def PyUnicode_AsUTF8(space, ref):
    return PyUnicode_AsUTF8AndSize(space, ref, cts.cast('Py_ssize_t *', 0))

@cpython_api([PyObject, rffi.CWCHARP, Py_ssize_t], Py_ssize_t, error=-1)
def PyUnicode_AsWideChar(space, ref, buf, size):
    """Copy the Unicode object contents into the wchar_t buffer w.  At most
    size wchar_t characters are copied (excluding a possibly trailing
    0-termination character).  Return the number of wchar_t characters
    copied or -1 in case of an error.  Note that the resulting wchar_t
    string may or may not be 0-terminated.  It is the responsibility of the caller
    to make sure that the wchar_t string is 0-terminated in case this is
    required by the application."""
    c_buffer = PyUnicode_AsUnicode(space, ref)
    c_length = get_wsize(ref)

    # If possible, try to copy the 0-termination as well
    if size > c_length:
        size = c_length + 1

    i = 0
    while i < size:
        buf[i] = c_buffer[i]
        i += 1

    if size > c_length:
        return c_length
    else:
        return size

@cpython_api([], rffi.CCHARP, error=CANNOT_FAIL)
def PyUnicode_GetDefaultEncoding(space):
    """Returns the currently active default encoding."""
    if default_encoding[0] == '\x00':
        encoding = unicodeobject.getdefaultencoding(space)
        i = 0
        while i < len(encoding) and i < DEFAULT_ENCODING_SIZE:
            default_encoding[i] = encoding[i]
            i += 1
    return default_encoding

@cpython_api([PyObject, CONST_STRING, CONST_STRING], PyObject)
def PyUnicode_AsEncodedObject(space, w_unicode, llencoding, llerrors):
    """Encode a Unicode object and return the result as Python object.
    encoding and errors have the same meaning as the parameters of the same name
    in the Unicode encode() method. The codec to be used is looked up using
    the Python codec registry. Return NULL if an exception was raised by the
    codec."""
    if not PyUnicode_Check(space, w_unicode):
        PyErr_BadArgument(space)

    encoding = errors = None
    if llencoding:
        encoding = rffi.charp2str(llencoding)
    if llerrors:
        errors = rffi.charp2str(llerrors)
    return unicodeobject.encode_object(space, w_unicode, encoding, errors)

@cpython_api([PyObject, CONST_STRING, CONST_STRING], PyObject)
def PyUnicode_AsEncodedString(space, w_unicode, llencoding, llerrors):
    """Encode a Unicode object and return the result as Python string object.
    encoding and errors have the same meaning as the parameters of the same name
    in the Unicode encode() method. The codec to be used is looked up using
    the Python codec registry. Return NULL if an exception was raised by the
    codec."""
    w_str = PyUnicode_AsEncodedObject(space, w_unicode, llencoding, llerrors)
    if not PyBytes_Check(space, w_str):
        raise oefmt(space.w_TypeError,
                    "encoder did not return a bytes object")
    return w_str

@cpython_api([PyObject], PyObject)
def PyUnicode_AsUnicodeEscapeString(space, w_unicode):
    """Encode a Unicode object using Unicode-Escape and return the result as Python
    string object.  Error handling is "strict". Return NULL if an exception was
    raised by the codec."""
    if not PyUnicode_Check(space, w_unicode):
        PyErr_BadArgument(space)

    return unicodeobject.encode_object(space, w_unicode, 'unicode-escape', 'strict')

@cpython_api([CONST_WSTRING, Py_ssize_t], PyObject, result_is_ll=True)
def PyUnicode_FromUnicode(space, wchar_p, length):
    """Create a Unicode Object from the Py_UNICODE buffer u of the given size. u
    may be NULL which causes the contents to be undefined. It is the user's
    responsibility to fill in the needed data.  The buffer is copied into the new
    object. If the buffer is not NULL, the return value might be a shared object.
    Therefore, modification of the resulting Unicode object is only allowed when u
    is NULL."""
    if length < 0:
        length = 0
    if wchar_p:
        s = wcharpsize2utf8(space, wchar_p, length)
        return make_ref(space, space.newutf8(s, length))
    else:
        return new_empty_unicode(space, length)

@cpython_api([PyObject, CONST_STRING], PyObject)
def _PyUnicode_AsDefaultEncodedString(space, w_unicode, errors):
    return PyUnicode_AsEncodedString(space, w_unicode, lltype.nullptr(rffi.CCHARP.TO), errors)

@cpython_api([CONST_STRING, Py_ssize_t, CONST_STRING, CONST_STRING], PyObject)
def PyUnicode_Decode(space, s, size, encoding, errors):
    """Create a Unicode object by decoding size bytes of the encoded string s.
    encoding and errors have the same meaning as the parameters of the same name
    in the unicode() built-in function.  The codec to be used is looked up
    using the Python codec registry.  Return NULL if an exception was raised by
    the codec."""
    return _pyunicode_decode(space, rffi.charpsize2str(s, size),
                             encoding, errors)

def _pyunicode_decode(space, s, encoding, errors):
    if encoding:
        w_encoding = space.newtext(rffi.charp2str(encoding))
    else:
        # python 3.4 changed to this from defaultencoding
        w_encoding = space.newtext('utf-8')
    w_str = space.newbytes(s)
    if errors:
        w_errors = space.newtext(rffi.charp2str(errors))
    else:
        w_errors = None
    return space.call_method(w_str, 'decode', w_encoding, w_errors)

@cpython_api([PyObject], PyObject)
def PyUnicode_FromObject(space, w_obj):
    """Copy an instance of a Unicode subtype to a new true Unicode object if
    necessary. If obj is already a true Unicode object (not a subtype), return
    the reference with incremented refcount.

    Objects other than Unicode or its subtypes will cause a TypeError.
    """
    if space.is_w(space.type(w_obj), space.w_unicode):
        return w_obj
    elif space.isinstance_w(w_obj, space.w_unicode):
        return space.call_function(space.w_unicode, w_obj)
    else:
        raise oefmt(space.w_TypeError,
                    "Can't convert '%T' object to str implicitly", w_obj)

@cpython_api([PyObject, CONST_STRING, CONST_STRING], PyObject)
def PyUnicode_FromEncodedObject(space, w_obj, encoding, errors):
    """Coerce an encoded object obj to an Unicode object and return a reference with
    incremented refcount.

    String and other char buffer compatible objects are decoded according to the
    given encoding and using the error handling defined by errors.  Both can be
    NULL to have the interface use the default values (see the next section for
    details).

    All other objects, including Unicode objects, cause a TypeError to be
    set."""
    if space.isinstance_w(w_obj, space.w_bytes):
        s = space.bytes_w(w_obj)
        if not s:
            return space.newtext('')
    elif space.isinstance_w(w_obj, space.w_unicode):
        raise oefmt(space.w_TypeError, "decoding str is not supported")
    elif space.isinstance_w(w_obj, space.w_bytearray):   # Python 2.x specific
        raise oefmt(space.w_TypeError, "decoding bytearray is not supported")
    else:
        s = space.charbuf_w(w_obj)
    return _pyunicode_decode(space, s, encoding, errors)


@cpython_api([PyObject, PyObjectP], rffi.INT_real, error=0)
def PyUnicode_FSConverter(space, w_obj, result):
    """ParseTuple converter: encode str objects to bytes using
    PyUnicode_EncodeFSDefault(); bytes objects are output as-is.
    result must be a PyBytesObject* which must be released when it is
    no longer used.
    """
    if not w_obj:
        # Implement ParseTuple cleanup support
        decref(space, result[0])
        return 1
    if space.isinstance_w(w_obj, space.w_bytes):
        w_output = w_obj
    else:
        w_obj = PyUnicode_FromObject(space, w_obj)
        w_output = space.fsencode(w_obj)
        if not space.isinstance_w(w_output, space.w_bytes):
            raise oefmt(space.w_TypeError, "encoder failed to return bytes")
    data = space.bytes0_w(w_output)  # Check for NUL bytes
    result[0] = make_ref(space, w_output)
    return Py_CLEANUP_SUPPORTED


@cpython_api([PyObject, PyObjectP], rffi.INT_real, error=0)
def PyUnicode_FSDecoder(space, w_obj, result):
    """ParseTuple converter: decode bytes objects to str using
    PyUnicode_DecodeFSDefaultAndSize(); str objects are output
    as-is. result must be a PyUnicodeObject* which must be released
    when it is no longer used.
    """
    if not w_obj:
        # Implement ParseTuple cleanup support
        decref(space, result[0])
        return 1
    if space.isinstance_w(w_obj, space.w_unicode):
        w_output = w_obj
    else:
        w_obj = PyBytes_FromObject(space, w_obj)
        w_output = space.fsdecode(w_obj)
        if not space.isinstance_w(w_output, space.w_unicode):
            raise oefmt(space.w_TypeError, "decoder failed to return unicode")
    data = space.utf8_0_w(w_output)  # Check for NUL bytes
    result[0] = make_ref(space, w_output)
    return Py_CLEANUP_SUPPORTED


@cpython_api([rffi.CCHARP, Py_ssize_t], PyObject)
def PyUnicode_DecodeFSDefaultAndSize(space, s, size):
    """Decode a string using Py_FileSystemDefaultEncoding and the
    'surrogateescape' error handler, or 'strict' on Windows.

    If Py_FileSystemDefaultEncoding is not set, fall back to the
    locale encoding.

    Use 'strict' error handler on Windows."""
    w_bytes = space.newbytes(rffi.charpsize2str(s, size))
    return space.fsdecode(w_bytes)


@cpython_api([rffi.CCHARP], PyObject)
def PyUnicode_DecodeFSDefault(space, s):
    """Decode a null-terminated string using Py_FileSystemDefaultEncoding
    and the 'surrogateescape' error handler, or 'strict' on Windows.

    If Py_FileSystemDefaultEncoding is not set, fall back to the
    locale encoding.

    Use PyUnicode_DecodeFSDefaultAndSize() if you know the string length.

    Use 'strict' error handler on Windows."""
    w_bytes = space.newbytes(rffi.charp2str(s))
    return space.fsdecode(w_bytes)


@cpython_api([PyObject], PyObject)
def PyUnicode_EncodeFSDefault(space, w_unicode):
    """Encode a Unicode object to Py_FileSystemDefaultEncoding with the
    'surrogateescape' error handler, or 'strict' on Windows, and return
    bytes. Note that the resulting bytes object may contain
    null bytes.

    If Py_FileSystemDefaultEncoding is not set, fall back to the
    locale encoding.
    """
    return space.fsencode(w_unicode)


@cpython_api([CONST_STRING], PyObject)
def PyUnicode_FromString(space, s):
    """Create a Unicode object from an UTF-8 encoded null-terminated char buffer"""
    w_str = space.newbytes(rffi.charp2str(s))
    return space.call_method(w_str, 'decode', space.newtext("utf-8"))

@cpython_api([PyObjectP], lltype.Void)
def PyUnicode_InternInPlace(space, string):
    """Intern the argument *string in place.  The argument must be the address
    of a pointer variable pointing to a Python unicode string object.  If there
    is an existing interned string that is the same as *string, it sets *string
    to it (decrementing the reference count of the old string object and
    incrementing the reference count of the interned string object), otherwise
    it leaves *string alone and interns it (incrementing its reference count).
    (Clarification: even though there is a lot of talk about reference counts,
    think of this function as reference-count-neutral; you own the object after
    the call if and only if you owned it before the call.)"""
    w_str = from_ref(space, string[0])
    w_str = space.new_interned_w_str(w_str)
    decref(space, string[0])
    string[0] = make_ref(space, w_str)


@cpython_api([CONST_STRING], PyObject)
def PyUnicode_InternFromString(space, s):
    """A combination of PyUnicode_FromString() and
    PyUnicode_InternInPlace(), returning either a new unicode string
    object that has been interned, or a new ("owned") reference to an
    earlier interned string object with the same value.
    """
    w_str = PyUnicode_FromString(space, s)
    return space.new_interned_w_str(w_str)

@cpython_api([CONST_STRING, Py_ssize_t], PyObject, result_is_ll=True)
def PyUnicode_FromStringAndSize(space, s, size):
    """Create a Unicode Object from the char buffer u. The bytes will be
    interpreted as being UTF-8 encoded. u may also be NULL which causes the
    contents to be undefined. It is the user's responsibility to fill in the
    needed data. The buffer is copied into the new object. If the buffer is not
    NULL, the return value might be a shared object. Therefore, modification of
    the resulting Unicode object is only allowed when u is NULL."""
    if s:
        return make_ref(space, PyUnicode_DecodeUTF8(
            space, s, size, lltype.nullptr(rffi.CCHARP.TO)))
    else:
        return new_empty_unicode(space, size)

@cpython_api([rffi.INT_real], PyObject)
def PyUnicode_FromOrdinal(space, ordinal):
    """Create a Unicode Object from the given Unicode code point ordinal.

    The ordinal must be in range(0x10000) on narrow Python builds
    (UCS2), and range(0x110000) on wide builds (UCS4). A ValueError is
    raised in case it is not."""
    w_ordinal = space.newint(rffi.cast(lltype.Signed, ordinal))
    return space.call_function(space.builtin.get('chr'), w_ordinal)

@cpython_api([PyObjectP, Py_ssize_t], rffi.INT_real, error=-1)
def PyUnicode_Resize(space, ref, newsize):
    # XXX always create a new string so far
    py_obj = ref[0]
    if not get_wbuffer(py_obj):
        raise oefmt(space.w_SystemError,
                    "PyUnicode_Resize called on already created string")
    try:
        py_newuni = new_empty_unicode(space, newsize)
    except MemoryError:
        decref(space, ref[0])
        ref[0] = lltype.nullptr(PyObject.TO)
        raise
    to_cp = newsize
    oldsize = get_wsize(py_obj)
    if oldsize < newsize:
        to_cp = oldsize
    for i in range(to_cp):
        get_wbuffer(py_newuni)[i] = get_wbuffer(py_obj)[i]
    decref(space, ref[0])
    ref[0] = rffi.cast(PyObject, py_newuni)
    return 0

def make_conversion_functions(suffix, encoding, only_for_asstring=False):
    @cpython_api([PyObject], PyObject)
    @func_renamer('PyUnicode_As%sString' % suffix)
    def PyUnicode_AsXXXString(space, w_unicode):
        """Encode a Unicode object and return the result as Python
        string object.  Error handling is "strict".  Return NULL if an
        exception was raised by the codec."""
        if not PyUnicode_Check(space, w_unicode):
            PyErr_BadArgument(space)
        return unicodeobject.encode_object(space, w_unicode, encoding, "strict")
    globals()['PyUnicode_As%sString' % suffix] = PyUnicode_AsXXXString

    if only_for_asstring:
        return

    @cpython_api([CONST_STRING, Py_ssize_t, CONST_STRING], PyObject)
    @func_renamer('PyUnicode_Decode%s' % suffix)
    def PyUnicode_DecodeXXX(space, s, size, errors):
        """Create a Unicode object by decoding size bytes of the
        encoded string s. Return NULL if an exception was raised by
        the codec.
        """
        w_s = space.newbytes(rffi.charpsize2str(s, size))
        if errors:
            w_errors = space.newtext(rffi.charp2str(errors))
        else:
            w_errors = None
        return space.call_method(w_s, 'decode', space.newtext(encoding), w_errors)
    globals()['PyUnicode_Decode%s' % suffix] = PyUnicode_DecodeXXX

    @cpython_api([CONST_WSTRING, Py_ssize_t, CONST_STRING], PyObject)
    @func_renamer('PyUnicode_Encode%s' % suffix)
    def PyUnicode_EncodeXXX(space, s, size, errors):
        """Encode the Py_UNICODE buffer of the given size and return a
        Python string object.  Return NULL if an exception was raised
        by the codec."""
        if size < 0:
            size = 0
        u = wcharpsize2utf8(space, s, size)
        w_u = space.newutf8(u, size)
        if errors:
            w_errors = space.newtext(rffi.charp2str(errors))
        else:
            w_errors = None
        return space.call_method(w_u, 'encode', space.newtext(encoding), w_errors)
    globals()['PyUnicode_Encode%s' % suffix] = PyUnicode_EncodeXXX

make_conversion_functions('UTF8', 'utf-8')
make_conversion_functions('UTF16', 'utf-16', only_for_asstring=True)
make_conversion_functions('UTF32', 'utf-32', only_for_asstring=True)
make_conversion_functions('ASCII', 'ascii')
make_conversion_functions('Latin1', 'latin-1')
if sys.platform == 'win32':
    make_conversion_functions('MBCS', 'mbcs')

@cpython_api([CONST_STRING, Py_ssize_t, CONST_STRING, INTP_real], PyObject)
def PyUnicode_DecodeUTF16(space, s, size, llerrors, pbyteorder):
    """Decode length bytes from a UTF-16 encoded buffer string and return the
    corresponding Unicode object.  errors (if non-NULL) defines the error
    handling. It defaults to "strict".

    If byteorder is non-NULL, the decoder starts decoding using the given byte
    order:

    *byteorder == -1: little endian
    *byteorder == 0:  native order
    *byteorder == 1:  big endian

    If *byteorder is zero, and the first two bytes of the input data are a
    byte order mark (BOM), the decoder switches to this byte order and the BOM is
    not copied into the resulting Unicode string.  If *byteorder is -1 or
    1, any byte order mark is copied to the output (where it will result in
    either a \ufeff or a \ufffe character).

    After completion, *byteorder is set to the current byte order at the end
    of input data.

    If byteorder is NULL, the codec starts in native order mode.

    Return NULL if an exception was raised by the codec."""

    string = rffi.charpsize2str(s, size)

    if pbyteorder is not None:
        llbyteorder = rffi.cast(lltype.Signed, pbyteorder[0])
        if llbyteorder < 0:
            byteorder = "little"
        elif llbyteorder > 0:
            byteorder = "big"
        else:
            byteorder = "native"
    else:
        byteorder = "native"

    if llerrors:
        errors = rffi.charp2str(llerrors)
    else:
        errors = 'strict'

    state = space.fromcache(CodecState)
    result, length, pos, bo = str_decode_utf_16_helper(
        string, errors, True, state.decode_error_handler,
        byteorder=byteorder)
    if pbyteorder is not None:
        pbyteorder[0] = rffi.cast(rffi.INT_real, bo)
    return space.newutf8(result, length)

@cpython_api([CONST_STRING, Py_ssize_t, CONST_STRING, INTP_real], PyObject)
def PyUnicode_DecodeUTF32(space, s, size, llerrors, pbyteorder):
    """Decode length bytes from a UTF-32 encoded buffer string and
    return the corresponding Unicode object.  errors (if non-NULL)
    defines the error handling. It defaults to "strict".

    If byteorder is non-NULL, the decoder starts decoding using the
    given byte order:
    *byteorder == -1: little endian
    *byteorder == 0:  native order
    *byteorder == 1:  big endian

    If *byteorder is zero, and the first four bytes of the input data
    are a byte order mark (BOM), the decoder switches to this byte
    order and the BOM is not copied into the resulting Unicode string.
    If *byteorder is -1 or 1, any byte order mark is copied to the
    output.

    After completion, *byteorder is set to the current byte order at
    the end of input data.

    In a narrow build codepoints outside the BMP will be decoded as
    surrogate pairs.

    If byteorder is NULL, the codec starts in native order mode.

    Return NULL if an exception was raised by the codec.
    """
    string = rffi.charpsize2str(s, size)

    if pbyteorder:
        llbyteorder = rffi.cast(lltype.Signed, pbyteorder[0])
        if llbyteorder < 0:
            byteorder = "little"
        elif llbyteorder > 0:
            byteorder = "big"
        else:
            byteorder = "native"
    else:
        byteorder = "native"

    if llerrors:
        errors = rffi.charp2str(llerrors)
    else:
        errors = 'strict'

    state = space.fromcache(CodecState)
    result, length, pos, bo = str_decode_utf_32_helper(
        string, errors, True, state.decode_error_handler,
        byteorder=byteorder)
    if pbyteorder is not None:
        pbyteorder[0] = rffi.cast(rffi.INT_real, bo)
    return space.newutf8(result, length)

@cpython_api([rffi.CWCHARP, Py_ssize_t, rffi.CCHARP, CONST_STRING],
             rffi.INT_real, error=-1)
def PyUnicode_EncodeDecimal(space, s, length, output, llerrors):
    """Takes a Unicode string holding a decimal value and writes it
    into an output buffer using standard ASCII digit codes.

    The output buffer has to provide at least length+1 bytes of
    storage area. The output string is 0-terminated.

    The encoder converts whitespace to ' ', decimal characters to
    their corresponding ASCII digit and all other Latin-1 characters
    except \0 as-is. Characters outside this range (Unicode ordinals
    1-256) are treated as errors. This includes embedded NULL bytes.

    Returns 0 on success, -1 on failure.
    """
    u = wcharpsize2utf8(space, s, length)
    if llerrors:
        errors = rffi.charp2str(llerrors)
    else:
        errors = None
    state = space.fromcache(CodecState)
    result = unicode_encode_decimal(u, errors, state.encode_error_handler)
    i = len(result)
    output[i] = '\0'
    i -= 1
    while i >= 0:
        output[i] = result[i]
        i -= 1
    return 0

@cpython_api([rffi.CArrayPtr(Py_UNICODE), Py_ssize_t], PyObject)
def PyUnicode_TransformDecimalToASCII(space, s, size):
    """Create a Unicode object by replacing all decimal digits in
    Py_UNICODE buffer of the given size by ASCII digits 0--9
    according to their decimal value.  Return NULL if an exception
    occurs."""
    result = rstring.UnicodeBuilder(size)
    for i in range(size):
        ch = s[i]
        if ord(ch) > 127:
            decimal = Py_UNICODE_TODECIMAL(space, ch)
            decimal = rffi.cast(lltype.Signed, decimal)
            if decimal >= 0:
                ch = unichr(ord('0') + decimal)
        result.append(ch)
    return space.newtext(result.build())

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-2)
def PyUnicode_Compare(space, w_left, w_right):
    """Compare two strings and return -1, 0, 1 for less than, equal, and greater
    than, respectively."""
    if space.is_true(space.lt(w_left, w_right)):
        return -1
    if space.is_true(space.lt(w_right, w_left)):
        return 1
    return 0

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_Concat(space, w_left, w_right):
    """Concat two strings giving a new Unicode string."""
    return space.add(w_left, w_right)

@cpython_api([PyObject, CONST_STRING], rffi.INT_real, error=CANNOT_FAIL)
def PyUnicode_CompareWithASCIIString(space, w_uni, string):
    """Compare a unicode object, uni, with string and return -1, 0, 1 for less
    than, equal, and greater than, respectively. It is best to pass only
    ASCII-encoded strings, but the function interprets the input string as
    ISO-8859-1 if it contains non-ASCII characters."""
    utf8 = space.utf8_w(w_uni)
    lgt = space.len_w(w_uni)
    i = 0
    # Compare Unicode string and source character set string
    for ch in rutf8.Utf8StringIterator(utf8):
        if string[i] == '\0':
            break
        s = ord(string[i])
        if ch != s:
            if ch < s:
                return -1
            else:
                return 1
        i += 1
    if i < lgt:
        return 1  # uni is longer
    if string[i] != '\0':
        return -1  # str is longer
    return 0


@cpython_api([rffi.CWCHARP, rffi.CWCHARP, Py_ssize_t], lltype.Void)
def Py_UNICODE_COPY(space, target, source, length):
    """Roughly equivalent to memcpy() only the base size is Py_UNICODE
    copies sizeof(Py_UNICODE) * length bytes from source to target"""
    for i in range(0, length):
        target[i] = source[i]

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_Format(space, w_format, w_args):
    """Return a new string object from format and args; this is analogous to
    format % args.  The args argument must be a tuple."""
    return space.mod(w_format, w_args)

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_Join(space, w_sep, w_seq):
    """Join a sequence of strings using the given separator and return
    the resulting Unicode string."""
    return space.call_method(w_sep, 'join', w_seq)

@cpython_api([PyObject, PyObject, PyObject, Py_ssize_t], PyObject)
def PyUnicode_Replace(space, w_str, w_substr, w_replstr, maxcount):
    """Replace at most maxcount occurrences of substr in str with replstr and
    return the resulting Unicode object. maxcount == -1 means replace all
    occurrences."""
    return space.call_method(w_str, "replace", w_substr, w_replstr,
                             space.newint(maxcount))

@cpython_api([PyObject, PyObject, Py_ssize_t, Py_ssize_t, rffi.INT_real],
             rffi.INT_real, error=-1)
def PyUnicode_Tailmatch(space, w_str, w_substr, start, end, direction):
    """Return 1 if substr matches str[start:end] at the given tail end
    (direction == -1 means to do a prefix match, direction == 1 a
    suffix match), 0 otherwise. Return -1 if an error occurred."""
    space.utf8_w(w_str)  # type check
    space.utf8_w(w_substr)
    w_start = space.newint(start)
    w_end = space.newint(end)
    if rffi.cast(lltype.Signed, direction) <= 0:
        w_result = space.call_method(
            w_str, "startswith", w_substr, w_start, w_end)
    else:
        w_result = space.call_method(
            w_str, "endswith", w_substr, w_start, w_end)
    return space.int_w(w_result)

@cpython_api([PyObject, PyObject, Py_ssize_t, Py_ssize_t], Py_ssize_t, error=-1)
def PyUnicode_Count(space, w_str, w_substr, start, end):
    """Return the number of non-overlapping occurrences of substr in
    str[start:end].  Return -1 if an error occurred."""
    w_count = space.call_method(w_str, "count", w_substr,
                                space.newint(start), space.newint(end))
    return space.int_w(w_count)

@cpython_api([PyObject, PyObject, Py_ssize_t, Py_ssize_t, rffi.INT_real],
             Py_ssize_t, error=-2)
def PyUnicode_Find(space, w_str, w_substr, start, end, direction):
    """Return the first position of substr in str*[*start:end] using
    the given direction (direction == 1 means to do a forward search,
    direction == -1 a backward search).  The return value is the index
    of the first match; a value of -1 indicates that no match was
    found, and -2 indicates that an error occurred and an exception
    has been set."""
    if rffi.cast(lltype.Signed, direction) > 0:
        w_pos = space.call_method(w_str, "find", w_substr,
                                  space.newint(start), space.newint(end))
    else:
        w_pos = space.call_method(w_str, "rfind", w_substr,
                                  space.newint(start), space.newint(end))
    return space.int_w(w_pos)

@cpython_api([PyObject, PyObject, Py_ssize_t], PyObject)
def PyUnicode_Split(space, w_str, w_sep, maxsplit):
    """Split a string giving a list of Unicode strings.  If sep is
    NULL, splitting will be done at all whitespace substrings.
    Otherwise, splits occur at the given separator.  At most maxsplit
    splits will be done.  If negative, no limit is set.  Separators
    are not included in the resulting list."""
    if w_sep is None:
        w_sep = space.w_None
    return space.call_method(w_str, "split", w_sep, space.newint(maxsplit))

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyUnicode_Splitlines(space, w_str, keepend):
    """Split a Unicode string at line breaks, returning a list of
    Unicode strings.  CRLF is considered to be one line break.  If
    keepend is 0, the Line break characters are not included in the
    resulting strings."""
    w_keepend = space.newbool(bool(rffi.cast(lltype.Signed, keepend)))
    return space.call_method(w_str, "splitlines", w_keepend)

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PyUnicode_Substring(space, w_str, start, end):
    return space.call_method(w_str, '__getitem__',
                         space.newslice(space.newint(start), space.newint(end),
                                        space.newint(1)))

@cts.decl("Py_UCS4 *PyUnicode_AsUCS4(PyObject *u, Py_UCS4 *buffer, Py_ssize_t buflen, int copy_null)")
def PyUnicode_AsUCS4(space, ref, pbuffer, buflen, copy_null):
    c_buffer = PyUnicode_AsUnicode(space, ref)
    c_length = get_wsize(ref)

    size = c_length
    if rffi.cast(lltype.Signed, copy_null):
        size += 1
    if not pbuffer:   # internal, for PyUnicode_AsUCS4Copy()
        pbuffer = lltype.malloc(rffi.CArray(Py_UCS4), size,
                                flavor='raw', track_allocation=False)
    elif buflen < size:
        raise oefmt(space.w_SystemError, "PyUnicode_AsUCS4: buflen too short")

    i = 0
    while i < size:
        pbuffer[i] = rffi.cast(Py_UCS4, c_buffer[i])
        i += 1
    return pbuffer

@cts.decl("Py_UCS4 *PyUnicode_AsUCS4Copy(PyObject *u)")
def PyUnicode_AsUCS4Copy(space, ref):
    return PyUnicode_AsUCS4(space, ref, cts.cast('Py_UCS4*', 0), 0,
                            rffi.cast(rffi.INT_real, 1))
