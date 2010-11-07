from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.unicodedata import unicodedb_4_1_0 as unicodedb
from pypy.module.cpyext.api import (
    CANNOT_FAIL, Py_ssize_t, build_type_checkers, cpython_api,
    bootstrap_function, PyObjectFields, cpython_struct, CONST_STRING,
    CONST_WSTRING)
from pypy.module.cpyext.pyerrors import PyErr_BadArgument
from pypy.module.cpyext.pyobject import PyObject, from_ref, make_typedescr
from pypy.module.sys.interp_encoding import setdefaultencoding
from pypy.objspace.std import unicodeobject, unicodetype
from pypy.rlib import runicode
import sys

## See comment in stringobject.py.  PyUnicode_FromUnicode(NULL, size) is not
## yet supported.

PyUnicodeObjectStruct = lltype.ForwardReference()
PyUnicodeObject = lltype.Ptr(PyUnicodeObjectStruct)
PyUnicodeObjectFields = (PyObjectFields +
    (("buffer", rffi.CWCHARP), ("size", Py_ssize_t)))
cpython_struct("PyUnicodeObject", PyUnicodeObjectFields, PyUnicodeObjectStruct)

@bootstrap_function
def init_unicodeobject(space):
    make_typedescr(space.w_unicode.instancetypedef,
                   basestruct=PyUnicodeObject.TO,
                   attach=unicode_attach,
                   dealloc=unicode_dealloc)

# Buffer for the default encoding (used by PyUnicde_GetDefaultEncoding)
DEFAULT_ENCODING_SIZE = 100
default_encoding = lltype.malloc(rffi.CCHARP.TO, DEFAULT_ENCODING_SIZE,
                                 flavor='raw', zero=True)

PyUnicode_Check, PyUnicode_CheckExact = build_type_checkers("Unicode", "w_unicode")

Py_UNICODE = lltype.UniChar

def unicode_attach(space, py_obj, w_obj):
    "Fills a newly allocated PyUnicodeObject with a unicode string"
    py_unicode = rffi.cast(PyUnicodeObject, py_obj)
    py_unicode.c_size = len(space.unicode_w(w_obj))
    py_unicode.c_buffer = lltype.nullptr(rffi.CWCHARP.TO)

@cpython_api([PyObject], lltype.Void, external=False)
def unicode_dealloc(space, py_obj):
    py_unicode = rffi.cast(PyUnicodeObject, py_obj)
    if py_unicode.c_buffer:
        lltype.free(py_unicode.c_buffer, flavor="raw")
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, py_obj)

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISSPACE(space, ch):
    """Return 1 or 0 depending on whether ch is a whitespace character."""
    return unicodedb.isspace(ord(ch))

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
def Py_UNICODE_ISLOWER(space, ch):
    """Return 1 or 0 depending on whether ch is a lowercase character."""
    return unicodedb.islower(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISUPPER(space, ch):
    """Return 1 or 0 depending on whether ch is an uppercase character."""
    return unicodedb.isupper(ord(ch))

@cpython_api([Py_UNICODE], Py_UNICODE, error=CANNOT_FAIL)
def Py_UNICODE_TOLOWER(space, ch):
    """Return the character ch converted to lower case."""
    return unichr(unicodedb.tolower(ord(ch)))

@cpython_api([Py_UNICODE], Py_UNICODE, error=CANNOT_FAIL)
def Py_UNICODE_TOUPPER(space, ch):
    """Return the character ch converted to upper case."""
    return unichr(unicodedb.toupper(ord(ch)))

@cpython_api([PyObject], rffi.CCHARP, error=CANNOT_FAIL)
def PyUnicode_AS_DATA(space, ref):
    """Return a pointer to the internal buffer of the object. o has to be a
    PyUnicodeObject (not checked)."""
    return rffi.cast(rffi.CCHARP, PyUnicode_AS_UNICODE(space, ref))

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PyUnicode_GET_DATA_SIZE(space, w_obj):
    """Return the size of the object's internal buffer in bytes.  o has to be a
    PyUnicodeObject (not checked)."""
    return rffi.sizeof(lltype.UniChar) * PyUnicode_GET_SIZE(space, w_obj)

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PyUnicode_GET_SIZE(space, w_obj):
    """Return the size of the object.  o has to be a PyUnicodeObject (not
    checked)."""
    assert isinstance(w_obj, unicodeobject.W_UnicodeObject)
    return space.int_w(space.len(w_obj))

@cpython_api([PyObject], rffi.CWCHARP, error=CANNOT_FAIL)
def PyUnicode_AS_UNICODE(space, ref):
    """Return a pointer to the internal Py_UNICODE buffer of the object.  ref
    has to be a PyUnicodeObject (not checked)."""
    ref_unicode = rffi.cast(PyUnicodeObject, ref)
    if not ref_unicode.c_buffer:
        # Copy unicode buffer
        w_unicode = from_ref(space, ref)
        u = space.unicode_w(w_unicode)
        ref_unicode.c_buffer = rffi.unicode2wcharp(u)
    return ref_unicode.c_buffer

@cpython_api([PyObject], rffi.CWCHARP, error=lltype.nullptr(rffi.CWCHARP.TO))
def PyUnicode_AsUnicode(space, ref):
    """Return a read-only pointer to the Unicode object's internal Py_UNICODE
    buffer, NULL if unicode is not a Unicode object."""
    if not PyUnicode_Check(space, ref):
        raise OperationError(space.w_TypeError,
                             space.wrap("expected unicode object"))
    return PyUnicode_AS_UNICODE(space, ref)

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyUnicode_GetSize(space, ref):
    if from_ref(space, rffi.cast(PyObject, ref.c_ob_type)) is space.w_unicode:
        ref = rffi.cast(PyUnicodeObject, ref)
        return ref.c_size
    else:
        w_obj = from_ref(space, ref)
        return space.int_w(space.len(w_obj))

@cpython_api([PyUnicodeObject, rffi.CWCHARP, Py_ssize_t], Py_ssize_t, error=-1)
def PyUnicode_AsWideChar(space, ref, buf, size):
    """Copy the Unicode object contents into the wchar_t buffer w.  At most
    size wchar_t characters are copied (excluding a possibly trailing
    0-termination character).  Return the number of wchar_t characters
    copied or -1 in case of an error.  Note that the resulting wchar_t
    string may or may not be 0-terminated.  It is the responsibility of the caller
    to make sure that the wchar_t string is 0-terminated in case this is
    required by the application."""
    c_buffer = PyUnicode_AS_UNICODE(space, rffi.cast(PyObject, ref))
    c_size = ref.c_size

    # If possible, try to copy the 0-termination as well
    if size > c_size:
        size = c_size + 1


    i = 0
    while i < size:
        buf[i] = c_buffer[i]
        i += 1

    if size > c_size:
        return c_size
    else:
        return size

@cpython_api([], rffi.CCHARP, error=CANNOT_FAIL)
def PyUnicode_GetDefaultEncoding(space):
    """Returns the currently active default encoding."""
    if default_encoding[0] == '\x00':
        encoding = unicodetype.getdefaultencoding(space)
        i = 0
        while i < len(encoding) and i < DEFAULT_ENCODING_SIZE:
            default_encoding[i] = encoding[i]
            i += 1
    return default_encoding

@cpython_api([CONST_STRING], rffi.INT_real, error=-1)
def PyUnicode_SetDefaultEncoding(space, encoding):
    """Sets the currently active default encoding. Returns 0 on
    success, -1 in case of an error."""
    w_encoding = space.wrap(rffi.charp2str(encoding))
    setdefaultencoding(space, w_encoding)
    default_encoding[0] = '\x00'
    return 0

@cpython_api([PyObject, CONST_STRING, CONST_STRING], PyObject)
def PyUnicode_AsEncodedString(space, w_unicode, llencoding, llerrors):
    """Encode a Unicode object and return the result as Python string object.
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
    return unicodetype.encode_object(space, w_unicode, encoding, errors)

@cpython_api([PyObject], PyObject)
def PyUnicode_AsUnicodeEscapeString(space, w_unicode):
    """Encode a Unicode object using Unicode-Escape and return the result as Python
    string object.  Error handling is "strict". Return NULL if an exception was
    raised by the codec."""
    if not PyUnicode_Check(space, w_unicode):
        PyErr_BadArgument(space)

    return unicodetype.encode_object(space, w_unicode, 'unicode-escape', 'strict')

@cpython_api([CONST_WSTRING, Py_ssize_t], PyObject)
def PyUnicode_FromUnicode(space, wchar_p, length):
    """Create a Unicode Object from the Py_UNICODE buffer u of the given size. u
    may be NULL which causes the contents to be undefined. It is the user's
    responsibility to fill in the needed data.  The buffer is copied into the new
    object. If the buffer is not NULL, the return value might be a shared object.
    Therefore, modification of the resulting Unicode object is only allowed when u
    is NULL."""
    if not wchar_p:
        raise NotImplementedError
    s = rffi.wcharpsize2unicode(wchar_p, length)
    return space.wrap(s)

@cpython_api([CONST_WSTRING, Py_ssize_t], PyObject)
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
    w_str = space.wrap(rffi.charpsize2str(s, size))
    w_encoding = space.wrap(rffi.charp2str(encoding))
    if errors:
        w_errors = space.wrap(rffi.charp2str(errors))
    else:
        w_errors = space.w_None
    return space.call_method(w_str, 'decode', w_encoding, w_errors)

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
    w_encoding = space.wrap(rffi.charp2str(encoding))
    if errors:
        w_errors = space.wrap(rffi.charp2str(errors))
    else:
        w_errors = space.w_None

    # - unicode is disallowed
    # - raise TypeError for non-string types
    if space.is_true(space.isinstance(w_obj, space.w_unicode)):
        w_meth = None
    else:
        try:
            w_meth = space.getattr(w_obj, space.wrap('decode'))
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
            w_meth = None
    if w_meth is None:
        raise OperationError(space.w_TypeError,
                             space.wrap("decoding Unicode is not supported"))
    return space.call_function(w_meth, w_encoding, w_errors)

@cpython_api([CONST_STRING], PyObject)
def PyUnicode_FromString(space, s):
    """Create a Unicode object from an UTF-8 encoded null-terminated char buffer"""
    w_str = space.wrap(rffi.charp2str(s))
    return space.call_method(w_str, 'decode', space.wrap("utf-8"))

@cpython_api([CONST_STRING, Py_ssize_t], PyObject)
def PyUnicode_FromStringAndSize(space, s, size):
    """Create a Unicode Object from the char buffer u. The bytes will be
    interpreted as being UTF-8 encoded. u may also be NULL which causes the
    contents to be undefined. It is the user's responsibility to fill in the
    needed data. The buffer is copied into the new object. If the buffer is not
    NULL, the return value might be a shared object. Therefore, modification of
    the resulting Unicode object is only allowed when u is NULL."""
    if not s:
        raise NotImplementedError
    w_str = space.wrap(rffi.charpsize2str(s, size))
    return space.call_method(w_str, 'decode', space.wrap("utf-8"))

@cpython_api([PyObject], PyObject)
def PyUnicode_AsUTF8String(space, w_unicode):
    """Encode a Unicode object using UTF-8 and return the result as Python string
    object.  Error handling is "strict".  Return NULL if an exception was raised
    by the codec."""
    if not PyUnicode_Check(space, w_unicode):
        PyErr_BadArgument(space)
    return unicodetype.encode_object(space, w_unicode, "utf-8", "strict")

@cpython_api([CONST_STRING, Py_ssize_t, CONST_STRING], PyObject)
def PyUnicode_DecodeUTF8(space, s, size, errors):
    """Create a Unicode object by decoding size bytes of the UTF-8 encoded string
    s. Return NULL if an exception was raised by the codec.
    """
    w_str = space.wrap(rffi.charpsize2str(s, size))
    if errors:
        w_errors = space.wrap(rffi.charp2str(errors))
    else:
        w_errors = space.w_None
    return space.call_method(w_str, 'decode', space.wrap("utf-8"), w_errors)

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
    
    Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""

    string = rffi.charpsize2str(s, size)

    #FIXME: I don't like these prefixes
    if pbyteorder is not None: # correct NULL check?
        llbyteorder = rffi.cast(lltype.Signed, pbyteorder[0]) # compatible with int?
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

    result, length, byteorder = runicode.str_decode_utf_16_helper(string, size,
                                           errors,
                                           True, # final ? false for multiple passes?
                                           None, # errorhandler
                                           byteorder)
    if pbyteorder is not None:
        pbyteorder[0] = rffi.cast(rffi.INT, byteorder)

    return space.wrap(result)

@cpython_api([PyObject], PyObject)
def PyUnicode_AsASCIIString(space, w_unicode):
    """Encode a Unicode object using ASCII and return the result as Python string
    object.  Error handling is "strict".  Return NULL if an exception was raised
    by the codec."""
    try:
        return space.call_method(w_unicode, 'encode', space.wrap('ascii')) #space.w_None for errors?
    except OperationError, e:
        if e.match(space, space.w_UnicodeEncodeError):
            return None
        else:
            raise

if sys.platform == 'win32':
    @cpython_api([CONST_WSTRING, Py_ssize_t, CONST_STRING], PyObject)
    def PyUnicode_EncodeMBCS(space, wchar_p, length, errors):
        """Encode the Py_UNICODE buffer of the given size using MBCS and return a
        Python string object.  Return NULL if an exception was raised by the codec.
        """
        w_unicode = space.wrap(rffi.wcharpsize2unicode(wchar_p, length))
        if errors:
            w_errors = space.wrap(rffi.charp2str(errors))
        else:
            w_errors = space.w_None
        return space.call_method(w_unicode, "encode",
                                 space.wrap("mbcs"), w_errors)

    @cpython_api([CONST_STRING, Py_ssize_t, CONST_STRING], PyObject)
    def PyUnicode_DecodeMBCS(space, s, size, errors):
        """Create a Unicode object by decoding size bytes of the MBCS encoded string s.
        Return NULL if an exception was raised by the codec.
        """
        w_str = space.wrap(rffi.charpsize2str(s, size))
        w_encoding = space.wrap("mbcs")
        if errors:
            w_errors = space.wrap(rffi.charp2str(errors))
        else:
            w_errors = space.w_None
        return space.call_method(w_str, 'decode', w_encoding, w_errors)
