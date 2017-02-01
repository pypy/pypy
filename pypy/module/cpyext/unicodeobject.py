from pypy.interpreter.error import OperationError, oefmt
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.runicode import unicode_encode_latin_1, unicode_encode_utf_16

from pypy.module.unicodedata import unicodedb
from pypy.module.cpyext.api import (
    CANNOT_FAIL, Py_ssize_t, build_type_checkers, cpython_api,
    bootstrap_function, CONST_STRING,
    CONST_WSTRING, Py_CLEANUP_SUPPORTED, slot_function, cts, parse_dir)
from pypy.module.cpyext.pyerrors import PyErr_BadArgument
from pypy.module.cpyext.pyobject import (
    PyObject, PyObjectP, Py_DecRef, make_ref, from_ref, track_reference,
    make_typedescr, get_typedescr, as_pyobj)
from pypy.module.cpyext.bytesobject import PyBytes_Check, PyBytes_FromObject
from pypy.module._codecs.interp_codecs import CodecState
from pypy.objspace.std import unicodeobject
from rpython.rlib import rstring, runicode
from rpython.tool.sourcetools import func_renamer
import sys

## See comment in bytesobject.py.

cts.parse_header(parse_dir / 'cpyext_unicodeobject.h')
PyUnicodeObject = cts.gettype('PyUnicodeObject*')
Py_UNICODE = cts.gettype('Py_UNICODE')

@bootstrap_function
def init_unicodeobject(space):
    make_typedescr(space.w_unicode.layout.typedef,
                   basestruct=PyUnicodeObject.TO,
                   attach=unicode_attach,
                   dealloc=unicode_dealloc,
                   realize=unicode_realize)

# Buffer for the default encoding (used by PyUnicde_GetDefaultEncoding)
DEFAULT_ENCODING_SIZE = 100
default_encoding = lltype.malloc(rffi.CCHARP.TO, DEFAULT_ENCODING_SIZE,
                                 flavor='raw', zero=True)

PyUnicode_Check, PyUnicode_CheckExact = build_type_checkers("Unicode", "w_unicode")

MAX_UNICODE = 1114111
WCHAR_KIND = 0
_1BYTE_KIND = 1
_2BYTE_KIND = 2
_4BYTE_KIND = 4


def new_empty_unicode(space, length):
    """
    Allocate a PyUnicodeObject and its buffer, but without a corresponding
    interpreter object.  The buffer may be mutated, until unicode_realize() is
    called.  Refcount of the result is 1.
    """
    typedescr = get_typedescr(space.w_unicode.layout.typedef)
    py_obj = typedescr.allocate(space, space.w_unicode)
    py_uni = rffi.cast(PyUnicodeObject, py_obj)

    buflen = length + 1
    set_wsize(py_uni, length)
    set_wbuffer(py_uni,
        lltype.malloc(
            rffi.CWCHARP.TO, buflen, flavor='raw', zero=True,
            add_memory_pressure=True))
    return py_uni

def unicode_attach(space, py_obj, w_obj, w_userdata=None):
    "Fills a newly allocated PyUnicodeObject with a unicode string"
    set_wsize(py_obj, len(space.unicode_w(w_obj)))
    set_wbuffer(py_obj, lltype.nullptr(rffi.CWCHARP.TO))

def unicode_realize(space, py_obj):
    """
    Creates the unicode in the interpreter. The PyUnicodeObject buffer must not
    be modified after this call.
    """
    py_uni = rffi.cast(PyUnicodeObject, py_obj)
    s = rffi.wcharpsize2unicode(get_wbuffer(py_uni), get_wsize(py_uni))
    w_type = from_ref(space, rffi.cast(PyObject, py_obj.c_ob_type))
    w_obj = space.allocate_instance(unicodeobject.W_UnicodeObject, w_type)
    w_obj.__init__(s)
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
    return get_state(py_obj).c_kind

def set_kind(py_obj, value):
    get_state(py_obj).c_kind = cts.cast('unsigned int', value)

def get_ascii(py_obj):
    return get_state(py_obj).c_ascii

def set_ascii(py_obj, value):
    get_state(py_obj).c_ascii = cts.cast('unsigned int', value)

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
    py_obj.c_utf8 = cts.cast('char *', buf)

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
    py_obj.c_data = cts.cast('void *', p_data)


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
    return runicode.UNICHR(runicode.MAXUNICODE)

@cts.decl("int _PyUnicode_Ready(PyObject *unicode)", error=-1)
def _PyUnicode_Ready(space, w_obj):
    assert isinstance(w_obj, unicodeobject.W_UnicodeObject)
    py_obj = as_pyobj(space, w_obj)
    assert get_kind(py_obj) == WCHAR_KIND
    maxchar = 0
    for c in w_obj._value:
        if ord(c) > maxchar:
            maxchar = ord(c)
            if maxchar > MAX_UNICODE:
                raise oefmt(space.w_ValueError,
                    "Character U+%d is not in range [U+0000; U+10ffff]",
                    maxchar)
    if maxchar < 256:
        ucs1_data = rffi.str2charp(unicode_encode_latin_1(
            w_obj._value, len(w_obj._value), errors='strict'))
        set_data(py_obj, ucs1_data)
        set_kind(py_obj, _1BYTE_KIND)
        if maxchar < 128:
            set_ascii(py_obj, 1)
            set_utf8(py_obj, get_data(py_obj))
            set_utf8_len(py_obj, get_wsize(py_obj))
        else:
            set_ascii(py_obj, 0)
            set_utf8(py_obj, 0)
            set_utf8_len(py_obj, 0)
        set_ready(py_obj, 1)
    elif maxchar < 65536:
        # XXX: assumes that sizeof(wchar_t) == 4
        ucs2_str = unicode_encode_utf_16(
            w_obj._value, len(w_obj._value), errors='strict')
        ucs2_data = cts.cast('Py_UCS2 *', rffi.str2charp(ucs2_str))
        set_data(py_obj, ucs2_data)
        set_len(py_obj, get_wsize(py_obj))
        set_kind(py_obj, _2BYTE_KIND)
        set_utf8(py_obj, 0)
        set_utf8_len(py_obj, 0)
        set_ready(py_obj, 1)
    else:
        # XXX: assumes that sizeof(wchar_t) == 4
        ucs4_data = get_wbuffer(py_obj)
        set_data(py_obj, ucs4_data)
        set_len(py_obj, get_wsize(py_obj))
        set_kind(py_obj, _4BYTE_KIND)
        set_utf8(py_obj, 0)
        set_utf8_len(py_obj, 0)
        set_ready(py_obj, 1)


@cpython_api([PyObject], rffi.CWCHARP)
def PyUnicode_AsUnicode(space, ref):
    """Return a read-only pointer to the Unicode object's internal Py_UNICODE
    buffer, NULL if unicode is not a Unicode object."""
    # Don't use PyUnicode_Check, it will realize the object :-(
    w_type = from_ref(space, rffi.cast(PyObject, ref.c_ob_type))
    if not space.issubtype_w(w_type, space.w_unicode):
        raise oefmt(space.w_TypeError, "expected unicode object")
    if not get_wbuffer(ref):
        # Copy unicode buffer
        w_unicode = from_ref(space, rffi.cast(PyObject, ref))
        u = space.unicode_w(w_unicode)
        set_wbuffer(ref, rffi.unicode2wcharp(u))
    return get_wbuffer(ref)

@cts.decl("char * PyUnicode_AsUTF8(PyObject *unicode)")
def PyUnicode_AsUTF8(space, ref):
    ref_unicode = rffi.cast(PyUnicodeObject, ref)
    if not get_utf8(ref_unicode):
        # Copy unicode buffer
        w_unicode = from_ref(space, ref)
        w_encoded = unicodeobject.encode_object(space, w_unicode, "utf-8",
                                                "strict")
        s = space.bytes_w(w_encoded)
        set_utf8(ref_unicode, rffi.str2charp(s))
    return get_utf8(ref_unicode)

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyUnicode_GetSize(space, ref):
    """Return the size of the deprecated Py_UNICODE representation, in code
    units (this includes surrogate pairs as 2 units).

    Please migrate to using PyUnicode_GetLength().
    """
    if from_ref(space, rffi.cast(PyObject, ref.c_ob_type)) is space.w_unicode:
        return get_wsize(ref)
    else:
        w_obj = from_ref(space, ref)
        return space.len_w(w_obj)

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyUnicode_GetLength(space, w_unicode):
    """Return the length of the Unicode object, in code points."""
    # XXX: this is a stub
    if not PyUnicode_Check(space, w_unicode):
        PyErr_BadArgument(space)
    #PyUnicode_READY(w_unicode)
    return PyUnicode_GET_LENGTH(space, w_unicode)

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
    if wchar_p:
        s = rffi.wcharpsize2unicode(wchar_p, length)
        return make_ref(space, space.wrap(s))
    else:
        return rffi.cast(PyObject, new_empty_unicode(space, length))

@cpython_api([CONST_WSTRING, Py_ssize_t], PyObject, result_is_ll=True)
def PyUnicode_FromWideChar(space, wchar_p, length):
    """Create a Unicode object from the wchar_t buffer w of the given size.
    Return NULL on failure."""
    # PyPy supposes Py_UNICODE == wchar_t
    return PyUnicode_FromUnicode(space, wchar_p, length)

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
    if not encoding:
        # This tracks CPython 2.7, in CPython 3.4 'utf-8' is hardcoded instead
        encoding = PyUnicode_GetDefaultEncoding(space)
    w_str = space.newbytes(rffi.charpsize2str(s, size))
    w_encoding = space.wrap(rffi.charp2str(encoding))
    if errors:
        w_errors = space.newbytes(rffi.charp2str(errors))
    else:
        w_errors = None
    return space.call_method(w_str, 'decode', w_encoding, w_errors)

@cpython_api([PyObject], PyObject)
def PyUnicode_FromObject(space, w_obj):
    """Shortcut for PyUnicode_FromEncodedObject(obj, NULL, "strict") which is used
    throughout the interpreter whenever coercion to Unicode is needed."""
    if space.is_w(space.type(w_obj), space.w_unicode):
        return w_obj
    else:
        return space.call_function(space.w_unicode, w_obj)

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
    if not encoding:
        raise oefmt(space.w_TypeError, "decoding Unicode is not supported")
    w_encoding = space.wrap(rffi.charp2str(encoding))
    if errors:
        w_errors = space.wrap(rffi.charp2str(errors))
    else:
        w_errors = None

    # - unicode is disallowed
    # - raise TypeError for non-string types
    if space.isinstance_w(w_obj, space.w_unicode):
        w_meth = None
    else:
        try:
            w_meth = space.getattr(w_obj, space.wrap('decode'))
        except OperationError as e:
            if not e.match(space, space.w_AttributeError):
                raise
            w_meth = None
    if w_meth is None:
        raise oefmt(space.w_TypeError, "decoding Unicode is not supported")
    return space.call_function(w_meth, w_encoding, w_errors)


@cpython_api([PyObject, PyObjectP], rffi.INT_real, error=0)
def PyUnicode_FSConverter(space, w_obj, result):
    """ParseTuple converter: encode str objects to bytes using
    PyUnicode_EncodeFSDefault(); bytes objects are output as-is.
    result must be a PyBytesObject* which must be released when it is
    no longer used.
    """
    if not w_obj:
        # Implement ParseTuple cleanup support
        Py_DecRef(space, result[0])
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
        Py_DecRef(space, result[0])
        return 1
    if space.isinstance_w(w_obj, space.w_unicode):
        w_output = w_obj
    else:
        w_obj = PyBytes_FromObject(space, w_obj)
        w_output = space.fsdecode(w_obj)
        if not space.isinstance_w(w_output, space.w_unicode):
            raise oefmt(space.w_TypeError, "decoder failed to return unicode")
    data = space.unicode0_w(w_output)  # Check for NUL bytes
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
    return space.call_method(w_str, 'decode', space.wrap("utf-8"))

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
        return rffi.cast(PyObject, new_empty_unicode(space, size))

@cpython_api([rffi.INT_real], PyObject)
def PyUnicode_FromOrdinal(space, ordinal):
    """Create a Unicode Object from the given Unicode code point ordinal.

    The ordinal must be in range(0x10000) on narrow Python builds
    (UCS2), and range(0x110000) on wide builds (UCS4). A ValueError is
    raised in case it is not."""
    w_ordinal = space.wrap(rffi.cast(lltype.Signed, ordinal))
    return space.call_function(space.builtin.get('chr'), w_ordinal)

@cpython_api([PyObjectP, Py_ssize_t], rffi.INT_real, error=-1)
def PyUnicode_Resize(space, ref, newsize):
    # XXX always create a new string so far
    py_uni = rffi.cast(PyUnicodeObject, ref[0])
    if not get_wbuffer(py_uni):
        raise oefmt(space.w_SystemError,
                    "PyUnicode_Resize called on already created string")
    try:
        py_newuni = new_empty_unicode(space, newsize)
    except MemoryError:
        Py_DecRef(space, ref[0])
        ref[0] = lltype.nullptr(PyObject.TO)
        raise
    to_cp = newsize
    oldsize = get_wsize(py_uni)
    if oldsize < newsize:
        to_cp = oldsize
    for i in range(to_cp):
        get_wbuffer(py_newuni)[i] = get_wbuffer(py_uni)[i]
    Py_DecRef(space, ref[0])
    ref[0] = rffi.cast(PyObject, py_newuni)
    return 0

def make_conversion_functions(suffix, encoding):
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

    @cpython_api([CONST_STRING, Py_ssize_t, CONST_STRING], PyObject)
    @func_renamer('PyUnicode_Decode%s' % suffix)
    def PyUnicode_DecodeXXX(space, s, size, errors):
        """Create a Unicode object by decoding size bytes of the
        encoded string s. Return NULL if an exception was raised by
        the codec.
        """
        w_s = space.newbytes(rffi.charpsize2str(s, size))
        if errors:
            w_errors = space.wrap(rffi.charp2str(errors))
        else:
            w_errors = None
        return space.call_method(w_s, 'decode', space.wrap(encoding), w_errors)
    globals()['PyUnicode_Decode%s' % suffix] = PyUnicode_DecodeXXX

    @cpython_api([CONST_WSTRING, Py_ssize_t, CONST_STRING], PyObject)
    @func_renamer('PyUnicode_Encode%s' % suffix)
    def PyUnicode_EncodeXXX(space, s, size, errors):
        """Encode the Py_UNICODE buffer of the given size and return a
        Python string object.  Return NULL if an exception was raised
        by the codec."""
        w_u = space.wrap(rffi.wcharpsize2unicode(s, size))
        if errors:
            w_errors = space.wrap(rffi.charp2str(errors))
        else:
            w_errors = None
        return space.call_method(w_u, 'encode', space.wrap(encoding), w_errors)
    globals()['PyUnicode_Encode%s' % suffix] = PyUnicode_EncodeXXX

make_conversion_functions('UTF8', 'utf-8')
make_conversion_functions('ASCII', 'ascii')
make_conversion_functions('Latin1', 'latin-1')
if sys.platform == 'win32':
    make_conversion_functions('MBCS', 'mbcs')

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, rffi.INTP], PyObject)
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
        errors = None

    result, length, byteorder = runicode.str_decode_utf_16_helper(
        string, size, errors,
        True, # final ? false for multiple passes?
        None, # errorhandler
        byteorder)
    if pbyteorder is not None:
        pbyteorder[0] = rffi.cast(rffi.INT, byteorder)

    return space.wrap(result)

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, rffi.INTP], PyObject)
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
        errors = None

    result, length, byteorder = runicode.str_decode_utf_32_helper(
        string, size, errors,
        True, # final ? false for multiple passes?
        None, # errorhandler
        byteorder)
    if pbyteorder is not None:
        pbyteorder[0] = rffi.cast(rffi.INT, byteorder)

    return space.wrap(result)

@cpython_api([rffi.CWCHARP, Py_ssize_t, rffi.CCHARP, rffi.CCHARP],
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
    u = rffi.wcharpsize2unicode(s, length)
    if llerrors:
        errors = rffi.charp2str(llerrors)
    else:
        errors = None
    state = space.fromcache(CodecState)
    result = runicode.unicode_encode_decimal(u, length, errors,
                                             state.encode_error_handler)
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
    return space.wrap(result.build())

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
    uni = space.unicode_w(w_uni)
    i = 0
    # Compare Unicode string and source character set string
    while i < len(uni) and string[i] != '\0':
        u = ord(uni[i])
        s = ord(string[i])
        if u != s:
            if u < s:
                return -1
            else:
                return 1
        i += 1
    if i < len(uni):
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
                             space.wrap(maxcount))

@cpython_api([PyObject, PyObject, Py_ssize_t, Py_ssize_t, rffi.INT_real],
             rffi.INT_real, error=-1)
def PyUnicode_Tailmatch(space, w_str, w_substr, start, end, direction):
    """Return 1 if substr matches str[start:end] at the given tail end
    (direction == -1 means to do a prefix match, direction == 1 a
    suffix match), 0 otherwise. Return -1 if an error occurred."""
    str = space.unicode_w(w_str)
    substr = space.unicode_w(w_substr)
    if rffi.cast(lltype.Signed, direction) <= 0:
        return rstring.startswith(str, substr, start, end)
    else:
        return rstring.endswith(str, substr, start, end)

@cpython_api([PyObject, PyObject, Py_ssize_t, Py_ssize_t], Py_ssize_t, error=-1)
def PyUnicode_Count(space, w_str, w_substr, start, end):
    """Return the number of non-overlapping occurrences of substr in
    str[start:end].  Return -1 if an error occurred."""
    w_count = space.call_method(w_str, "count", w_substr,
                                space.wrap(start), space.wrap(end))
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
                                  space.wrap(start), space.wrap(end))
    else:
        w_pos = space.call_method(w_str, "rfind", w_substr,
                                  space.wrap(start), space.wrap(end))
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
    return space.call_method(w_str, "split", w_sep, space.wrap(maxsplit))

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyUnicode_Splitlines(space, w_str, keepend):
    """Split a Unicode string at line breaks, returning a list of
    Unicode strings.  CRLF is considered to be one line break.  If
    keepend is 0, the Line break characters are not included in the
    resulting strings."""
    return space.call_method(w_str, "splitlines", space.wrap(keepend))
