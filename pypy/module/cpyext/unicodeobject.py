from pypy.interpreter.error import OperationError, oefmt
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.unicodedata import unicodedb
from pypy.module.cpyext.api import (
    CANNOT_FAIL, Py_ssize_t, build_type_checkers, cpython_api,
    bootstrap_function, CONST_STRING,
    CONST_WSTRING, slot_function, cts, parse_dir)
from pypy.module.cpyext.pyerrors import PyErr_BadArgument
from pypy.module.cpyext.pyobject import (
    PyObject, PyObjectP, Py_DecRef, make_ref, from_ref, track_reference,
    make_typedescr, get_typedescr)
from pypy.module.cpyext.bytesobject import PyString_Check
from pypy.module.sys.interp_encoding import setdefaultencoding
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
    py_uni.c_length = length
    py_uni.c_str = lltype.malloc(rffi.CWCHARP.TO, buflen,
                                 flavor='raw', zero=True,
                                 add_memory_pressure=True)
    py_uni.c_hash = -1
    py_uni.c_defenc = lltype.nullptr(PyObject.TO)
    return py_uni

def unicode_attach(space, py_obj, w_obj, w_userdata=None):
    "Fills a newly allocated PyUnicodeObject with a unicode string"
    py_unicode = rffi.cast(PyUnicodeObject, py_obj)
    s = space.unicode_w(w_obj)
    py_unicode.c_length = len(s)
    py_unicode.c_str = lltype.nullptr(rffi.CWCHARP.TO)
    py_unicode.c_hash = space.hash_w(space.newunicode(s))
    py_unicode.c_defenc = lltype.nullptr(PyObject.TO)

def unicode_realize(space, py_obj):
    """
    Creates the unicode in the interpreter. The PyUnicodeObject buffer must not
    be modified after this call.
    """
    py_uni = rffi.cast(PyUnicodeObject, py_obj)
    s = rffi.wcharpsize2unicode(py_uni.c_str, py_uni.c_length)
    w_type = from_ref(space, rffi.cast(PyObject, py_obj.c_ob_type))
    w_obj = space.allocate_instance(unicodeobject.W_UnicodeObject, w_type)
    w_obj.__init__(s)
    py_uni.c_hash = space.hash_w(space.newunicode(s))
    track_reference(space, py_obj, w_obj)
    return w_obj

@slot_function([PyObject], lltype.Void)
def unicode_dealloc(space, py_obj):
    py_unicode = rffi.cast(PyUnicodeObject, py_obj)
    Py_DecRef(space, py_unicode.c_defenc)
    if py_unicode.c_str:
        lltype.free(py_unicode.c_str, flavor="raw")

    from pypy.module.cpyext.object import _dealloc
    _dealloc(space, py_obj)

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

@cpython_api([rffi.VOIDP], rffi.CCHARP, error=CANNOT_FAIL)
def PyUnicode_AS_DATA(space, ref):
    """Return a pointer to the internal buffer of the object. o has to be a
    PyUnicodeObject (not checked)."""
    return rffi.cast(rffi.CCHARP, PyUnicode_AS_UNICODE(space, ref))

@cpython_api([rffi.VOIDP], Py_ssize_t, error=CANNOT_FAIL)
def PyUnicode_GET_DATA_SIZE(space, w_obj):
    """Return the size of the object's internal buffer in bytes.  o has to be a
    PyUnicodeObject (not checked)."""
    return rffi.sizeof(Py_UNICODE) * PyUnicode_GET_SIZE(space, w_obj)

@cpython_api([rffi.VOIDP], Py_ssize_t, error=CANNOT_FAIL)
def PyUnicode_GET_SIZE(space, w_obj):
    """Return the size of the object.  obj is a PyUnicodeObject (not
    checked)."""
    return space.len_w(w_obj)

@cpython_api([rffi.VOIDP], rffi.CWCHARP, error=CANNOT_FAIL)
def PyUnicode_AS_UNICODE(space, ref):
    """Return a pointer to the internal Py_UNICODE buffer of the object.  ref
    has to be a PyUnicodeObject (not checked)."""
    ref_unicode = rffi.cast(PyUnicodeObject, ref)
    if not ref_unicode.c_str:
        # Copy unicode buffer
        w_unicode = from_ref(space, rffi.cast(PyObject, ref))
        u = space.unicode_w(w_unicode)
        ref_unicode.c_str = rffi.unicode2wcharp(u)
    return ref_unicode.c_str

@cpython_api([PyObject], rffi.CWCHARP)
def PyUnicode_AsUnicode(space, ref):
    """Return a read-only pointer to the Unicode object's internal Py_UNICODE
    buffer, NULL if unicode is not a Unicode object."""
    # Don't use PyUnicode_Check, it will realize the object :-(
    w_type = from_ref(space, rffi.cast(PyObject, ref.c_ob_type))
    if not space.issubtype_w(w_type, space.w_unicode):
        raise oefmt(space.w_TypeError, "expected unicode object")
    return PyUnicode_AS_UNICODE(space, rffi.cast(rffi.VOIDP, ref))

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyUnicode_GetSize(space, ref):
    if from_ref(space, rffi.cast(PyObject, ref.c_ob_type)) is space.w_unicode:
        ref = rffi.cast(PyUnicodeObject, ref)
        return ref.c_length
    else:
        w_obj = from_ref(space, ref)
        return space.len_w(w_obj)

@cpython_api([PyUnicodeObject, rffi.CWCHARP, Py_ssize_t], Py_ssize_t, error=-1)
def PyUnicode_AsWideChar(space, ref, buf, size):
    """Copy the Unicode object contents into the wchar_t buffer w.  At most
    size wchar_t characters are copied (excluding a possibly trailing
    0-termination character).  Return the number of wchar_t characters
    copied or -1 in case of an error.  Note that the resulting wchar_t
    string may or may not be 0-terminated.  It is the responsibility of the caller
    to make sure that the wchar_t string is 0-terminated in case this is
    required by the application."""
    c_str = PyUnicode_AS_UNICODE(space, rffi.cast(rffi.VOIDP, ref))
    c_length = ref.c_length

    # If possible, try to copy the 0-termination as well
    if size > c_length:
        size = c_length + 1


    i = 0
    while i < size:
        buf[i] = c_str[i]
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

@cpython_api([CONST_STRING], rffi.INT_real, error=-1)
def PyUnicode_SetDefaultEncoding(space, encoding):
    """Sets the currently active default encoding. Returns 0 on
    success, -1 in case of an error."""
    if not encoding:
        PyErr_BadArgument(space)
    w_encoding = space.newtext(rffi.charp2str(encoding))
    setdefaultencoding(space, w_encoding)
    default_encoding[0] = '\x00'
    return 0

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
    if not PyString_Check(space, w_str):
        raise oefmt(space.w_TypeError,
                    "encoder did not return a string object")
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
        return make_ref(space, space.newunicode(s))
    else:
        return rffi.cast(PyObject, new_empty_unicode(space, length))

@cpython_api([CONST_WSTRING, Py_ssize_t], PyObject, result_is_ll=True)
def PyUnicode_FromWideChar(space, wchar_p, length):
    """Create a Unicode object from the wchar_t buffer w of the given size.
    Return NULL on failure."""
    # PyPy supposes Py_UNICODE == wchar_t
    return PyUnicode_FromUnicode(space, wchar_p, length)

@cpython_api([PyObject, CONST_STRING], PyObject, result_is_ll=True)
def _PyUnicode_AsDefaultEncodedString(space, ref, errors):
    # Returns a borrowed reference.
    py_uni = rffi.cast(PyUnicodeObject, ref)
    if not py_uni.c_defenc:
        py_uni.c_defenc = make_ref(
            space, PyUnicode_AsEncodedString(
                space, ref,
                lltype.nullptr(rffi.CCHARP.TO), errors))
    return py_uni.c_defenc

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
    w_encoding = space.newtext(rffi.charp2str(encoding))
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
    w_encoding = space.newtext(rffi.charp2str(encoding))
    if errors:
        w_errors = space.newtext(rffi.charp2str(errors))
    else:
        w_errors = None

    # - unicode is disallowed
    # - raise TypeError for non-string types
    if space.isinstance_w(w_obj, space.w_unicode):
        w_meth = None
    else:
        try:
            w_meth = space.getattr(w_obj, space.newtext('decode'))
        except OperationError as e:
            if not e.match(space, space.w_AttributeError):
                raise
            w_meth = None
    if w_meth is None:
        raise oefmt(space.w_TypeError, "decoding Unicode is not supported")
    return space.call_function(w_meth, w_encoding, w_errors)

@cpython_api([CONST_STRING], PyObject)
def PyUnicode_FromString(space, s):
    """Create a Unicode object from an UTF-8 encoded null-terminated char buffer"""
    w_str = space.newbytes(rffi.charp2str(s))
    return space.call_method(w_str, 'decode', space.newtext("utf-8"))

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
    w_ordinal = space.newint(rffi.cast(lltype.Signed, ordinal))
    return space.call_function(space.builtin.get('unichr'), w_ordinal)

@cpython_api([PyObjectP, Py_ssize_t], rffi.INT_real, error=-1)
def PyUnicode_Resize(space, ref, newsize):
    # XXX always create a new string so far
    py_uni = rffi.cast(PyUnicodeObject, ref[0])
    if not py_uni.c_str:
        raise oefmt(space.w_SystemError,
                    "PyUnicode_Resize called on already created string")
    try:
        py_newuni = new_empty_unicode(space, newsize)
    except MemoryError:
        Py_DecRef(space, ref[0])
        ref[0] = lltype.nullptr(PyObject.TO)
        raise
    to_cp = newsize
    oldsize = py_uni.c_length
    if oldsize < newsize:
        to_cp = oldsize
    for i in range(to_cp):
        py_newuni.c_str[i] = py_uni.c_str[i]
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
        w_u = space.newunicode(rffi.wcharpsize2unicode(s, size))
        if errors:
            w_errors = space.newtext(rffi.charp2str(errors))
        else:
            w_errors = None
        return space.call_method(w_u, 'encode', space.newtext(encoding), w_errors)
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

    return space.newunicode(result)

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

    return space.newunicode(result)

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

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-2)
def PyUnicode_Compare(space, w_left, w_right):
    """Compare two strings and return -1, 0, 1 for less than, equal, and greater
    than, respectively."""
    return space.int_w(space.cmp(w_left, w_right))

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_Concat(space, w_left, w_right):
    """Concat two strings giving a new Unicode string."""
    return space.add(w_left, w_right)

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
