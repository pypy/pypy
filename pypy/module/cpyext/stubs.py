from pypy.module.cpyext.api import (
    cpython_api, PyObject, PyObjectP, CANNOT_FAIL
    )
from pypy.module.cpyext.complexobject import Py_complex_ptr as Py_complex
from pypy.rpython.lltypesystem import rffi, lltype

# we don't really care
PyTypeObjectPtr = rffi.VOIDP
Py_ssize_t = rffi.SSIZE_T
PyMethodDef = rffi.VOIDP
PyGetSetDef = rffi.VOIDP
PyMemberDef = rffi.VOIDP
Py_buffer = rffi.VOIDP
va_list = rffi.VOIDP
PyDateTime_Date = rffi.VOIDP
PyDateTime_DateTime = rffi.VOIDP
PyDateTime_Time = rffi.VOIDP
wrapperbase = rffi.VOIDP
FILE = rffi.VOIDP
PyFileObject = rffi.VOIDP
PyCodeObject = rffi.VOIDP
PyFrameObject = rffi.VOIDP
PyFloatObject = rffi.VOIDP
_inittab = rffi.VOIDP
PyThreadState = rffi.VOIDP
PyInterpreterState = rffi.VOIDP
Py_UNICODE = lltype.UniChar
PyCompilerFlags = rffi.VOIDP
_node = rffi.VOIDP
Py_tracefunc = rffi.VOIDP

@cpython_api([PyObject], lltype.Void)
def _PyObject_Del(space, op):
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyObject_CheckBuffer(space, obj):
    """Return 1 if obj supports the buffer interface otherwise 0."""
    raise NotImplementedError

@cpython_api([PyObject, Py_buffer, rffi.INT_real], rffi.INT_real, error=-1)
def PyObject_GetBuffer(space, obj, view, flags):
    """Export obj into a Py_buffer, view.  These arguments must
    never be NULL.  The flags argument is a bit field indicating what
    kind of buffer the caller is prepared to deal with and therefore what
    kind of buffer the exporter is allowed to return.  The buffer interface
    allows for complicated memory sharing possibilities, but some caller may
    not be able to handle all the complexity but may want to see if the
    exporter will let them take a simpler view to its memory.
    
    Some exporters may not be able to share memory in every possible way and
    may need to raise errors to signal to some consumers that something is
    just not possible. These errors should be a BufferError unless
    there is another error that is actually causing the problem. The
    exporter can use flags information to simplify how much of the
    Py_buffer structure is filled in with non-default values and/or
    raise an error if the object can't support a simpler view of its memory.
    
    0 is returned on success and -1 on error.
    
    The following table gives possible values to the flags arguments.
    
    Flag
    
    Description
    
    PyBUF_SIMPLE
    
    This is the default flag state.  The returned
    buffer may or may not have writable memory.  The
    format of the data will be assumed to be unsigned
    bytes.  This is a "stand-alone" flag constant. It
    never needs to be '|'d to the others. The exporter
    will raise an error if it cannot provide such a
    contiguous buffer of bytes.
    
    PyBUF_WRITABLE
    
    The returned buffer must be writable.  If it is
    not writable, then raise an error.
    
    PyBUF_STRIDES
    
    This implies PyBUF_ND. The returned
    buffer must provide strides information (i.e. the
    strides cannot be NULL). This would be used when
    the consumer can handle strided, discontiguous
    arrays.  Handling strides automatically assumes
    you can handle shape.  The exporter can raise an
    error if a strided representation of the data is
    not possible (i.e. without the suboffsets).
    
    PyBUF_ND
    
    The returned buffer must provide shape
    information. The memory will be assumed C-style
    contiguous (last dimension varies the
    fastest). The exporter may raise an error if it
    cannot provide this kind of contiguous buffer. If
    this is not given then shape will be NULL.
    
    PyBUF_C_CONTIGUOUS
    PyBUF_F_CONTIGUOUS
    PyBUF_ANY_CONTIGUOUS
    
    These flags indicate that the contiguity returned
    buffer must be respectively, C-contiguous (last
    dimension varies the fastest), Fortran contiguous
    (first dimension varies the fastest) or either
    one.  All of these flags imply
    PyBUF_STRIDES and guarantee that the
    strides buffer info structure will be filled in
    correctly.
    
    PyBUF_INDIRECT
    
    This flag indicates the returned buffer must have
    suboffsets information (which can be NULL if no
    suboffsets are needed).  This can be used when
    the consumer can handle indirect array
    referencing implied by these suboffsets. This
    implies PyBUF_STRIDES.
    
    PyBUF_FORMAT
    
    The returned buffer must have true format
    information if this flag is provided. This would
    be used when the consumer is going to be checking
    for what 'kind' of data is actually stored. An
    exporter should always be able to provide this
    information if requested. If format is not
    explicitly requested then the format must be
    returned as NULL (which means 'B', or
    unsigned bytes)
    
    PyBUF_STRIDED
    
    This is equivalent to (PyBUF_STRIDES |
    PyBUF_WRITABLE).
    
    PyBUF_STRIDED_RO
    
    This is equivalent to (PyBUF_STRIDES).
    
    PyBUF_RECORDS
    
    This is equivalent to (PyBUF_STRIDES |
    PyBUF_FORMAT | PyBUF_WRITABLE).
    
    PyBUF_RECORDS_RO
    
    This is equivalent to (PyBUF_STRIDES |
    PyBUF_FORMAT).
    
    PyBUF_FULL
    
    This is equivalent to (PyBUF_INDIRECT |
    PyBUF_FORMAT | PyBUF_WRITABLE).
    
    PyBUF_FULL_RO
    
    This is equivalent to (PyBUF_INDIRECT |
    PyBUF_FORMAT).
    
    PyBUF_CONTIG
    
    This is equivalent to (PyBUF_ND |
    PyBUF_WRITABLE).
    
    PyBUF_CONTIG_RO
    
    This is equivalent to (PyBUF_ND)."""
    raise NotImplementedError

@cpython_api([Py_buffer], lltype.Void)
def PyBuffer_Release(space, view):
    """Release the buffer view.  This should be called when the buffer
    is no longer being used as it may free memory from it."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], Py_ssize_t, error=CANNOT_FAIL)
def PyBuffer_SizeFromFormat(space, format):
    """Return the implied ~Py_buffer.itemsize from the struct-stype
    ~Py_buffer.format."""
    raise NotImplementedError

@cpython_api([Py_buffer, lltype.Char], rffi.INT_real, error=CANNOT_FAIL)
def PyBuffer_IsContiguous(space, view, fortran):
    """Return 1 if the memory defined by the view is C-style (fortran is
    'C') or Fortran-style (fortran is 'F') contiguous or either one
    (fortran is 'A').  Return 0 otherwise."""
    raise NotImplementedError

@cpython_api([rffi.INT_real, Py_ssize_t, Py_ssize_t, Py_ssize_t, lltype.Char], lltype.Void)
def PyBuffer_FillContiguousStrides(space, ndim, shape, strides, itemsize, fortran):
    """Fill the strides array with byte-strides of a contiguous (C-style if
    fortran is 'C' or Fortran-style if fortran is 'F' array of the
    given shape with the given number of bytes per element."""
    raise NotImplementedError

@cpython_api([Py_buffer, PyObject, rffi.VOIDP, Py_ssize_t, rffi.INT_real, rffi.INT_real], rffi.INT_real, error=-1)
def PyBuffer_FillInfo(space, view, obj, buf, len, readonly, infoflags):
    """Fill in a buffer-info structure, view, correctly for an exporter that can
    only share a contiguous chunk of memory of "unsigned bytes" of the given
    length.  Return 0 on success and -1 (with raising an error) on error."""
    raise NotImplementedError

@cpython_api([Py_buffer], PyObject)
def PyMemoryView_FromBuffer(space, view):
    """Create a memoryview object wrapping the given buffer-info structure view.
    The memoryview object then owns the buffer, which means you shouldn't
    try to release it yourself: it will be released on deallocation of the
    memoryview object."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real, lltype.Char], PyObject)
def PyMemoryView_GetContiguous(space, obj, buffertype, order):
    """Create a memoryview object to a contiguous chunk of memory (in either
    'C' or 'F'ortran order) from an object that defines the buffer
    interface. If memory is contiguous, the memoryview object points to the
    original memory. Otherwise copy is made and the memoryview points to a
    new bytes object."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyMemoryView_Check(space, obj):
    """Return true if the object obj is a memoryview object.  It is not
    currently allowed to create subclasses of memoryview."""
    raise NotImplementedError

@cpython_api([PyObject], Py_buffer)
def PyMemoryView_GET_BUFFER(space, obj):
    """Return a pointer to the buffer-info structure wrapped by the given
    object.  The object must be a memoryview instance; this macro doesn't
    check its type, you must do it yourself or you will risk crashes."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyByteArray_Check(space, o):
    """Return true if the object o is a bytearray object or an instance of a
    subtype of the bytearray type."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyByteArray_CheckExact(space, o):
    """Return true if the object o is a bytearray object, but not an instance of a
    subtype of the bytearray type."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyByteArray_FromObject(space, o):
    """Return a new bytearray object from any object, o, that implements the
    buffer protocol.
    
    XXX expand about the buffer protocol, at least somewhere"""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t], PyObject)
def PyByteArray_FromStringAndSize(space, string, len):
    """Create a new bytearray object from string and its length, len.  On
    failure, NULL is returned."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyByteArray_Concat(space, a, b):
    """Concat bytearrays a and b and return a new bytearray with the result."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyByteArray_Size(space, bytearray):
    """Return the size of bytearray after checking for a NULL pointer."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyByteArray_AsString(space, bytearray):
    """Return the contents of bytearray as a char array after checking for a
    NULL pointer."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], rffi.INT_real, error=-1)
def PyByteArray_Resize(space, bytearray, len):
    """Resize the internal buffer of bytearray to len."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyByteArray_AS_STRING(space, bytearray):
    """Macro version of PyByteArray_AsString()."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyByteArray_GET_SIZE(space, bytearray):
    """Macro version of PyByteArray_Size()."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyCell_Check(space, ob):
    """Return true if ob is a cell object; ob must not be NULL."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyCell_New(space, ob):
    """Create and return a new cell object containing the value ob. The parameter may
    be NULL."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyCell_Get(space, cell):
    """Return the contents of the cell cell."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyCell_GET(space, cell):
    """Return the contents of the cell cell, but without checking that cell is
    non-NULL and a cell object."""
    borrow_from()
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyCell_Set(space, cell, value):
    """Set the contents of the cell object cell to value.  This releases the
    reference to any current content of the cell. value may be NULL.  cell
    must be non-NULL; if it is not a cell object, -1 will be returned.  On
    success, 0 will be returned."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], lltype.Void)
def PyCell_SET(space, cell, value):
    """Sets the value of the cell object cell to value.  No reference counts are
    adjusted, and no checks are made for safety; cell must be non-NULL and must
    be a cell object."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyClass_IsSubclass(space, klass, base):
    """Return true if klass is a subclass of base. Return false in all other cases."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyInstance_New(space, cls, arg, kw):
    """Create a new instance of a specific class.  The parameters arg and kw are
    used as the positional and keyword parameters to the object's constructor."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyCode_Check(space, co):
    """Return true if co is a code object"""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyCode_GetNumFree(space, co):
    """Return the number of free variables in co."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PyCodec_Register(space, search_function):
    """Register a new codec search function.
    
    As side effect, this tries to load the encodings package, if not yet
    done, to make sure that it is always first in the list of search functions."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyCodec_Encode(space, object, encoding, errors):
    """Generic codec based encoding API.
    
    object is passed through the encoder function found for the given
    encoding using the error handling method defined by errors.  errors may
    be NULL to use the default method defined for the codec.  Raises a
    LookupError if no encoder can be found."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyCodec_Decode(space, object, encoding, errors):
    """Generic codec based decoding API.
    
    object is passed through the decoder function found for the given
    encoding using the error handling method defined by errors.  errors may
    be NULL to use the default method defined for the codec.  Raises a
    LookupError if no encoder can be found."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], PyObject)
def PyCodec_Encoder(space, encoding):
    """Get an encoder function for the given encoding."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], PyObject)
def PyCodec_Decoder(space, encoding):
    """Get a decoder function for the given encoding."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject, rffi.CCHARP], PyObject)
def PyCodec_StreamReader(space, encoding, stream, errors):
    """Get a StreamReader factory function for the given encoding."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject, rffi.CCHARP], PyObject)
def PyCodec_StreamWriter(space, encoding, stream, errors):
    """Get a StreamWriter factory function for the given encoding."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject], rffi.INT_real, error=-1)
def PyCodec_RegisterError(space, name, error):
    """Register the error handling callback function error under the given name.
    This callback function will be called by a codec when it encounters
    unencodable characters/undecodable bytes and name is specified as the error
    parameter in the call to the encode/decode function.
    
    The callback gets a single argument, an instance of
    UnicodeEncodeError, UnicodeDecodeError or
    UnicodeTranslateError that holds information about the problematic
    sequence of characters or bytes and their offset in the original string (see
    unicodeexceptions for functions to extract this information).  The
    callback must either raise the given exception, or return a two-item tuple
    containing the replacement for the problematic sequence, and an integer
    giving the offset in the original string at which encoding/decoding should be
    resumed.
    
    Return 0 on success, -1 on error."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], PyObject)
def PyCodec_LookupError(space, name):
    """Lookup the error handling callback function registered under name.  As a
    special case NULL can be passed, in which case the error handling callback
    for "strict" will be returned."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyCodec_StrictErrors(space, exc):
    """Raise exc as an exception."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyCodec_IgnoreErrors(space, exc):
    """Ignore the unicode error, skipping the faulty input."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyCodec_ReplaceErrors(space, exc):
    """Replace the unicode encode error with ? or U+FFFD."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyCodec_XMLCharRefReplaceErrors(space, exc):
    """Replace the unicode encode error with XML character references."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyCodec_BackslashReplaceErrors(space, exc):
    r"""Replace the unicode encode error with backslash escapes (\x, \u and
    \U)."""
    raise NotImplementedError

@cpython_api([Py_complex, Py_complex], Py_complex)
def _Py_c_sum(space, left, right):
    """Return the sum of two complex numbers, using the C Py_complex
    representation."""
    raise NotImplementedError

@cpython_api([Py_complex, Py_complex], Py_complex)
def _Py_c_diff(space, left, right):
    """Return the difference between two complex numbers, using the C
    Py_complex representation."""
    raise NotImplementedError

@cpython_api([Py_complex], Py_complex)
def _Py_c_neg(space, complex):
    """Return the negation of the complex number complex, using the C
    Py_complex representation."""
    raise NotImplementedError

@cpython_api([Py_complex, Py_complex], Py_complex)
def _Py_c_prod(space, left, right):
    """Return the product of two complex numbers, using the C Py_complex
    representation."""
    raise NotImplementedError

@cpython_api([Py_complex, Py_complex], Py_complex)
def _Py_c_quot(space, dividend, divisor):
    """Return the quotient of two complex numbers, using the C Py_complex
    representation."""
    raise NotImplementedError

@cpython_api([Py_complex, Py_complex], Py_complex)
def _Py_c_pow(space, num, exp):
    """Return the exponentiation of num by exp, using the C Py_complex
    representation."""
    raise NotImplementedError

@cpython_api([Py_complex], PyObject)
def PyComplex_FromCComplex(space, v):
    """Create a new Python complex number object from a C Py_complex value."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARPP, PyObject], rffi.DOUBLE, error=-1.0)
def PyOS_string_to_double(space, s, endptr, overflow_exception):
    """Convert a string s to a double, raising a Python
    exception on failure.  The set of accepted strings corresponds to
    the set of strings accepted by Python's float() constructor,
    except that s must not have leading or trailing whitespace.
    The conversion is independent of the current locale.
    
    If endptr is NULL, convert the whole string.  Raise
    ValueError and return -1.0 if the string is not a valid
    representation of a floating-point number.
    
    If endptr is not NULL, convert as much of the string as
    possible and set *endptr to point to the first unconverted
    character.  If no initial segment of the string is the valid
    representation of a floating-point number, set *endptr to point
    to the beginning of the string, raise ValueError, and return
    -1.0.
    
    If s represents a value that is too large to store in a float
    (for example, "1e500" is such a string on many platforms) then
    if overflow_exception is NULL return Py_HUGE_VAL (with
    an appropriate sign) and don't set any exception.  Otherwise,
    overflow_exception must point to a Python exception object;
    raise that exception and return -1.0.  In both cases, set
    *endptr to point to the first character after the converted value.
    
    If any other error occurs during the conversion (for example an
    out-of-memory error), set the appropriate Python exception and
    return -1.0.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARPP], rffi.DOUBLE, error=CANNOT_FAIL)
def PyOS_ascii_strtod(space, nptr, endptr):
    """Convert a string to a double. This function behaves like the Standard C
    function strtod() does in the C locale. It does this without changing the
    current locale, since that would not be thread-safe.
    
    PyOS_ascii_strtod() should typically be used for reading configuration
    files or other non-user input that should be locale independent.
    
    See the Unix man page strtod(2) for details.
    
    Use PyOS_string_to_double() instead."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.SIZE_T, rffi.CCHARP, rffi.DOUBLE], rffi.CCHARP)
def PyOS_ascii_formatd(space, buffer, buf_len, format, d):
    """Convert a double to a string using the '.' as the decimal
    separator. format is a printf()-style format string specifying the
    number format. Allowed conversion characters are 'e', 'E', 'f',
    'F', 'g' and 'G'.
    
    The return value is a pointer to buffer with the converted string or NULL if
    the conversion failed.
    
    This function is removed in Python 2.7 and 3.1.  Use PyOS_double_to_string()
    instead."""
    raise NotImplementedError

@cpython_api([rffi.DOUBLE, lltype.Char, rffi.INT_real, rffi.INT_real, rffi.INTP], rffi.CCHARP)
def PyOS_double_to_string(space, val, format_code, precision, flags, ptype):
    """Convert a double val to a string using supplied
    format_code, precision, and flags.
    
    format_code must be one of 'e', 'E', 'f', 'F',
    'g', 'G' or 'r'.  For 'r', the supplied precision
    must be 0 and is ignored.  The 'r' format code specifies the
    standard repr() format.
    
    flags can be zero or more of the values Py_DTSF_SIGN,
    Py_DTSF_ADD_DOT_0, or Py_DTSF_ALT, or-ed together:
    
    Py_DTSF_SIGN means to always precede the returned string with a sign
    character, even if val is non-negative.
    
    Py_DTSF_ADD_DOT_0 means to ensure that the returned string will not look
    like an integer.
    
    Py_DTSF_ALT means to apply "alternate" formatting rules.  See the
    documentation for the PyOS_snprintf() '#' specifier for
    details.
    
    If ptype is non-NULL, then the value it points to will be set to one of
    Py_DTST_FINITE, Py_DTST_INFINITE, or Py_DTST_NAN, signifying that
    val is a finite number, an infinite number, or not a number, respectively.
    
    The return value is a pointer to buffer with the converted string or
    NULL if the conversion failed. The caller is responsible for freeing the
    returned string by calling PyMem_Free().
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP], rffi.DOUBLE, error=CANNOT_FAIL)
def PyOS_ascii_atof(space, nptr):
    """Convert a string to a double in a locale-independent way.
    
    See the Unix man page atof(2) for details.
    
    Use PyOS_string_to_double() instead."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP], rffi.CCHARP)
def PyOS_stricmp(space, s1, s2):
    """Case insensitive comparison of strings. The function works almost
    identically to strcmp() except that it ignores the case.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP, Py_ssize_t], rffi.CCHARP)
def PyOS_strnicmp(space, s1, s2, size):
    """Case insensitive comparison of strings. The function works almost
    identically to strncmp() except that it ignores the case.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyTZInfo_Check(space, ob):
    """Return true if ob is of type PyDateTime_TZInfoType or a subtype of
    PyDateTime_TZInfoType.  ob must not be NULL.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyTZInfo_CheckExact(space, ob):
    """Return true if ob is of type PyDateTime_TZInfoType. ob must not be
    NULL.
    """
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, PyGetSetDef], PyObject)
def PyDescr_NewGetSet(space, type, getset):
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, PyMemberDef], PyObject)
def PyDescr_NewMember(space, type, meth):
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, PyMethodDef], PyObject)
def PyDescr_NewMethod(space, type, meth):
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, wrapperbase, rffi.VOIDP], PyObject)
def PyDescr_NewWrapper(space, type, wrapper, wrapped):
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, PyMethodDef], PyObject)
def PyDescr_NewClassMethod(space, type, method):
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyDescr_IsData(space, descr):
    """Return true if the descriptor objects descr describes a data attribute, or
    false if it describes a method.  descr must be a descriptor object; there is
    no error checking.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyWrapper_New(space, w_d, w_self):
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyDictProxy_New(space, dict):
    """Return a proxy object for a mapping which enforces read-only behavior.
    This is normally used to create a proxy to prevent modification of the
    dictionary for non-dynamic class types.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.INT_real], rffi.INT_real, error=-1)
def PyDict_Merge(space, a, b, override):
    """Iterate over mapping object b adding key-value pairs to dictionary a.
    b may be a dictionary, or any object supporting PyMapping_Keys()
    and PyObject_GetItem(). If override is true, existing pairs in a
    will be replaced if a matching key is found in b, otherwise pairs will
    only be added if there is not a matching key in a. Return 0 on
    success or -1 if an exception was raised.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.INT_real], rffi.INT_real, error=-1)
def PyDict_MergeFromSeq2(space, a, seq2, override):
    """Update or merge into dictionary a, from the key-value pairs in seq2.
    seq2 must be an iterable object producing iterable objects of length 2,
    viewed as key-value pairs.  In case of duplicate keys, the last wins if
    override is true, else the first wins. Return 0 on success or -1
    if an exception was raised. Equivalent Python (except for the return
    value):
    
    def PyDict_MergeFromSeq2(a, seq2, override):
        for key, value in seq2:
            if override or key not in a:
                a[key] = value
    """
    raise NotImplementedError

@cpython_api([rffi.INT_real], PyObject)
def PyErr_SetFromWindowsErr(space, ierr):
    """This is a convenience function to raise WindowsError. If called with
    ierr of 0, the error code returned by a call to GetLastError()
    is used instead.  It calls the Win32 function FormatMessage() to retrieve
    the Windows description of error code given by ierr or GetLastError(),
    then it constructs a tuple object whose first item is the ierr value and whose
    second item is the corresponding error message (gotten from
    FormatMessage()), and then calls PyErr_SetObject(PyExc_WindowsError,
    object). This function always returns NULL. Availability: Windows.
    Return value: always NULL."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyErr_SetExcFromWindowsErr(space, type, ierr):
    """Similar to PyErr_SetFromWindowsErr(), with an additional parameter
    specifying the exception type to be raised. Availability: Windows.
    
    Return value: always NULL."""
    raise NotImplementedError

@cpython_api([rffi.INT_real, rffi.CCHARP], PyObject)
def PyErr_SetFromWindowsErrWithFilename(space, ierr, filename):
    """Similar to PyErr_SetFromWindowsErr(), with the additional behavior that
    if filename is not NULL, it is passed to the constructor of
    WindowsError as a third parameter. Availability: Windows.
    Return value: always NULL."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real, rffi.CCHARP], PyObject)
def PyErr_SetExcFromWindowsErrWithFilename(space, type, ierr, filename):
    """Similar to PyErr_SetFromWindowsErrWithFilename(), with an additional
    parameter specifying the exception type to be raised. Availability: Windows.
    
    Return value: always NULL."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP, rffi.INT_real, rffi.CCHARP, PyObject], rffi.INT_real, error=-1)
def PyErr_WarnExplicit(space, category, message, filename, lineno, module, registry):
    """Issue a warning message with explicit control over all warning attributes.  This
    is a straightforward wrapper around the Python function
    warnings.warn_explicit(), see there for more information.  The module
    and registry arguments may be set to NULL to get the default effect
    described there."""
    raise NotImplementedError

@cpython_api([rffi.INT_real], rffi.INT_real, error=CANNOT_FAIL)
def PySignal_SetWakeupFd(space, fd):
    """This utility function specifies a file descriptor to which a '\0' byte will
    be written whenever a signal is received.  It returns the previous such file
    descriptor.  The value -1 disables the feature; this is the initial state.
    This is equivalent to signal.set_wakeup_fd() in Python, but without any
    error checking.  fd should be a valid file descriptor.  The function should
    only be called from the main thread."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP, Py_ssize_t, Py_ssize_t, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicodeDecodeError_Create(space, encoding, object, length, start, end, reason):
    """Create a UnicodeDecodeError object with the attributes encoding,
    object, length, start, end and reason."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CWCHARP, Py_ssize_t, Py_ssize_t, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicodeEncodeError_Create(space, encoding, object, length, start, end, reason):
    """Create a UnicodeEncodeError object with the attributes encoding,
    object, length, start, end and reason."""
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t, Py_ssize_t, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicodeTranslateError_Create(space, object, length, start, end, reason):
    """Create a UnicodeTranslateError object with the attributes object,
    length, start, end and reason."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicodeDecodeError_GetEncoding(space, exc):
    """Return the encoding attribute of the given exception object."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicodeDecodeError_GetObject(space, exc):
    """Return the object attribute of the given exception object."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], rffi.INT_real, error=-1)
def PyUnicodeDecodeError_GetStart(space, exc, start):
    """Get the start attribute of the given exception object and place it into
    *start.  start must not be NULL.  Return 0 on success, -1 on
    failure."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], rffi.INT_real, error=-1)
def PyUnicodeDecodeError_SetStart(space, exc, start):
    """Set the start attribute of the given exception object to start.  Return
    0 on success, -1 on failure."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], rffi.INT_real, error=-1)
def PyUnicodeDecodeError_GetEnd(space, exc, end):
    """Get the end attribute of the given exception object and place it into
    *end.  end must not be NULL.  Return 0 on success, -1 on
    failure."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], rffi.INT_real, error=-1)
def PyUnicodeDecodeError_SetEnd(space, exc, end):
    """Set the end attribute of the given exception object to end.  Return 0
    on success, -1 on failure."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicodeDecodeError_GetReason(space, exc):
    """Return the reason attribute of the given exception object."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real, error=-1)
def PyUnicodeDecodeError_SetReason(space, exc, reason):
    """Set the reason attribute of the given exception object to reason.  Return
    0 on success, -1 on failure."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], rffi.INT_real, error=1)
def Py_EnterRecursiveCall(space, where):
    """Marks a point where a recursive C-level call is about to be performed.
    
    If USE_STACKCHECK is defined, this function checks if the the OS
    stack overflowed using PyOS_CheckStack().  In this is the case, it
    sets a MemoryError and returns a nonzero value.
    
    The function then checks if the recursion limit is reached.  If this is the
    case, a RuntimeError is set and a nonzero value is returned.
    Otherwise, zero is returned.
    
    where should be a string such as " in instance check" to be
    concatenated to the RuntimeError message caused by the recursion depth
    limit."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def Py_LeaveRecursiveCall(space):
    """Ends a Py_EnterRecursiveCall().  Must be called once for each
    successful invocation of Py_EnterRecursiveCall()."""
    raise NotImplementedError

@cpython_api([PyFileObject], lltype.Void)
def PyFile_IncUseCount(space, p):
    """Increments the PyFileObject's internal use count to indicate
    that the underlying FILE* is being used.
    This prevents Python from calling f_close() on it from another thread.
    Callers of this must call PyFile_DecUseCount() when they are
    finished with the FILE*.  Otherwise the file object will
    never be closed by Python.
    
    The GIL must be held while calling this function.
    
    The suggested use is to call this after PyFile_AsFile() and before
    you release the GIL:
    
    FILE *fp = PyFile_AsFile(p);
    PyFile_IncUseCount(p);
    /* ... */
    Py_BEGIN_ALLOW_THREADS
    do_something(fp);
    Py_END_ALLOW_THREADS
    /* ... */
    PyFile_DecUseCount(p);
    """
    raise NotImplementedError

@cpython_api([PyFileObject], lltype.Void)
def PyFile_DecUseCount(space, p):
    """Decrements the PyFileObject's internal unlocked_count member to
    indicate that the caller is done with its own use of the FILE*.
    This may only be called to undo a prior call to PyFile_IncUseCount().
    
    The GIL must be held while calling this function (see the example
    above).
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyFile_Name(space, p):
    """Return the name of the file specified by p as a string object."""
    borrow_from()
    raise NotImplementedError

@cpython_api([PyFileObject, rffi.CCHARP], rffi.INT_real, error=0)
def PyFile_SetEncoding(space, p, enc):
    """Set the file's encoding for Unicode output to enc. Return 1 on success and 0
    on failure.
    """
    raise NotImplementedError

@cpython_api([PyFileObject, rffi.CCHARP, rffi.CCHARP], rffi.INT_real, error=0)
def PyFile_SetEncodingAndErrors(space, p, enc, errors):
    """Set the file's encoding for Unicode output to enc, and its error
    mode to err. Return 1 on success and 0 on failure.
    """
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], rffi.INT_real, error=CANNOT_FAIL)
def PyFile_SoftSpace(space, p, newflag):
    """
    This function exists for internal use by the interpreter.  Set the
    softspace attribute of p to newflag and return the previous value.
    p does not have to be a file object for this function to work properly; any
    object is supported (thought its only interesting if the softspace
    attribute can be set).  This function clears any errors, and will return 0
    as the previous value if the attribute either does not exist or if there were
    errors in retrieving it.  There is no way to detect errors from this function,
    but doing so should not be needed."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.INT_real], rffi.INT_real, error=-1)
def PyFile_WriteObject(space, obj, p, flags):
    """
    Write object obj to file object p.  The only supported flag for flags is
    Py_PRINT_RAW; if given, the str() of the object is written
    instead of the repr().  Return 0 on success or -1 on failure; the
    appropriate exception will be set."""
    raise NotImplementedError

@cpython_api([], PyObject)
def PyFloat_GetInfo(space):
    """Return a structseq instance which contains information about the
    precision, minimum and maximum values of a float. It's a thin wrapper
    around the header file float.h.
    """
    raise NotImplementedError

@cpython_api([], rffi.DOUBLE, error=CANNOT_FAIL)
def PyFloat_GetMax(space):
    """Return the maximum representable finite float DBL_MAX as C double.
    """
    raise NotImplementedError

@cpython_api([], rffi.DOUBLE, error=CANNOT_FAIL)
def PyFloat_GetMin(space):
    """Return the minimum normalized positive float DBL_MIN as C double.
    """
    raise NotImplementedError

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def PyFloat_ClearFreeList(space):
    """Clear the float free list. Return the number of items that could not
    be freed.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyFloatObject], lltype.Void)
def PyFloat_AsString(space, buf, v):
    """Convert the argument v to a string, using the same rules as
    str(). The length of buf should be at least 100.
    
    This function is unsafe to call because it writes to a buffer whose
    length it does not know.
    
    Use PyObject_Str() or PyOS_double_to_string() instead."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyFloatObject], lltype.Void)
def PyFloat_AsReprString(space, buf, v):
    """Same as PyFloat_AsString, except uses the same rules as
    repr().  The length of buf should be at least 100.
    
    This function is unsafe to call because it writes to a buffer whose
    length it does not know.
    
    Use PyObject_Repr() or PyOS_double_to_string() instead."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyFunction_New(space, code, globals):
    """Return a new function object associated with the code object code. globals
    must be a dictionary with the global variables accessible to the function.
    
    The function's docstring, name and __module__ are retrieved from the code
    object, the argument defaults and closure are set to NULL."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyFunction_GetCode(space, op):
    """Return the code object associated with the function object op."""
    borrow_from()
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyFunction_GetGlobals(space, op):
    """Return the globals dictionary associated with the function object op."""
    borrow_from()
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyFunction_GetModule(space, op):
    """Return the __module__ attribute of the function object op. This is normally
    a string containing the module name, but can be set to any other object by
    Python code."""
    borrow_from()
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyFunction_GetDefaults(space, op):
    """Return the argument default values of the function object op. This can be a
    tuple of arguments or NULL."""
    borrow_from()
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyFunction_SetDefaults(space, op, defaults):
    """Set the argument default values for the function object op. defaults must be
    Py_None or a tuple.
    
    Raises SystemError and returns -1 on failure."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyFunction_GetClosure(space, op):
    """Return the closure associated with the function object op. This can be NULL
    or a tuple of cell objects."""
    borrow_from()
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyFunction_SetClosure(space, op, closure):
    """Set the closure associated with the function object op. closure must be
    Py_None or a tuple of cell objects.
    
    Raises SystemError and returns -1 on failure."""
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, Py_ssize_t], PyObject)
def PyObject_GC_NewVar(space, type, size):
    """Analogous to PyObject_NewVar() but for container objects with the
    Py_TPFLAGS_HAVE_GC flag set.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PyObject_GC_Resize(space, op, newsize):
    """Resize an object allocated by PyObject_NewVar().  Returns the
    resized object or NULL on failure.
    
    This function used an int type for newsize. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def _PyObject_GC_TRACK(space, op):
    """A macro version of PyObject_GC_Track().  It should not be used for
    extension modules."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def _PyObject_GC_UNTRACK(space, op):
    """A macro version of PyObject_GC_UnTrack().  It should not be used for
    extension modules."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyGen_Check(space, ob):
    """Return true if ob is a generator object; ob must not be NULL."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyGen_CheckExact(space, ob):
    """Return true if ob's type is PyGen_Type is a generator object; ob must not
    be NULL."""
    raise NotImplementedError

@cpython_api([PyFrameObject], PyObject)
def PyGen_New(space, frame):
    """Create and return a new generator object based on the frame object. A
    reference to frame is stolen by this function. The parameter must not be
    NULL."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject, PyObject, PyObject], PyObject)
def PyImport_ImportModuleEx(space, name, globals, locals, fromlist):
    """Import a module.  This is best described by referring to the built-in
    Python function __import__(), as the standard __import__() function calls
    this function directly.
    
    The return value is a new reference to the imported module or top-level package,
    or NULL with an exception set on failure (before Python 2.4, the module may
    still be created in this case).  Like for __import__(), the return value
    when a submodule of a package was requested is normally the top-level package,
    unless a non-empty fromlist was given.
    
    Failing imports remove incomplete module objects.
    
    The function is an alias for PyImport_ImportModuleLevel() with
    -1 as level, meaning relative import."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject, PyObject, PyObject, rffi.INT_real], PyObject)
def PyImport_ImportModuleLevel(space, name, globals, locals, fromlist, level):
    """Import a module.  This is best described by referring to the built-in Python
    function __import__(), as the standard __import__() function calls
    this function directly.
    
    The return value is a new reference to the imported module or top-level package,
    or NULL with an exception set on failure.  Like for __import__(),
    the return value when a submodule of a package was requested is normally the
    top-level package, unless a non-empty fromlist was given.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyImport_ReloadModule(space, m):
    """Reload a module.  This is best described by referring to the built-in
    Python function reload(), as the standard reload() function calls this
    function directly.  Return a new reference to the reloaded module, or NULL
    with an exception set on failure (the module still exists in this case)."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject], PyObject)
def PyImport_ExecCodeModule(space, name, co):
    """Given a module name (possibly of the form package.module) and a code
    object read from a Python bytecode file or obtained from the built-in
    function compile(), load the module.  Return a new reference to the module
    object, or NULL with an exception set if an error occurred.  Before Python
    2.4, the module could still be created in error cases.  Starting with Python
    2.4, name is removed from sys.modules in error cases, and even if name was
    already in sys.modules on entry to PyImport_ExecCodeModule().  Leaving
    incompletely initialized modules in sys.modules is dangerous, as imports of
    such modules have no way to know that the module object is an unknown (and
    probably damaged with respect to the module author's intents) state.
    
    The module's __file__ attribute will be set to the code object's
    co_filename.
    
    This function will reload the module if it was already imported.  See
    PyImport_ReloadModule() for the intended way to reload a module.
    
    If name points to a dotted name of the form package.module, any package
    structures not already created will still not be created.
    
    name is removed from sys.modules in error cases."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject, rffi.CCHARP], PyObject)
def PyImport_ExecCodeModuleEx(space, name, co, pathname):
    """Like PyImport_ExecCodeModule(), but the __file__ attribute of
    the module object is set to pathname if it is non-NULL."""
    raise NotImplementedError

@cpython_api([], lltype.Signed, error=CANNOT_FAIL)
def PyImport_GetMagicNumber(space):
    """Return the magic number for Python bytecode files (a.k.a. .pyc and
    .pyo files).  The magic number should be present in the first four bytes
    of the bytecode file, in little-endian byte order."""
    raise NotImplementedError

@cpython_api([], PyObject)
def PyImport_GetModuleDict(space):
    """Return the dictionary used for the module administration (a.k.a.
    sys.modules).  Note that this is a per-interpreter variable."""
    borrow_from()
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyImport_GetImporter(space, path):
    """Return an importer object for a sys.path/pkg.__path__ item
    path, possibly by fetching it from the sys.path_importer_cache
    dict.  If it wasn't yet cached, traverse sys.path_hooks until a hook
    is found that can handle the path item.  Return None if no hook could;
    this tells our caller it should fall back to the built-in import mechanism.
    Cache the result in sys.path_importer_cache.  Return a new reference
    to the importer object.
    """
    raise NotImplementedError

@cpython_api([], lltype.Void)
def _PyImport_Init(space):
    """Initialize the import mechanism.  For internal use only."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyImport_Cleanup(space):
    """Empty the module table.  For internal use only."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def _PyImport_Fini(space):
    """Finalize the import mechanism.  For internal use only."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP], PyObject)
def _PyImport_FindExtension(space, name, filename):
    """For internal use only."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP], PyObject)
def _PyImport_FixupExtension(space, name, filename):
    """For internal use only."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], rffi.INT_real, error=-1)
def PyImport_ImportFrozenModule(space, name):
    """Load a frozen module named name.  Return 1 for success, 0 if the
    module is not found, and -1 with an exception set if the initialization
    failed.  To access the imported module on a successful load, use
    PyImport_ImportModule().  (Note the misnomer --- this function would
    reload the module if it was already imported.)"""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.VOIDP], rffi.INT_real, error=-1)
def PyImport_AppendInittab(space, name, initfunc):
    """Add a single module to the existing table of built-in modules.  This is a
    convenience wrapper around PyImport_ExtendInittab(), returning -1 if
    the table could not be extended.  The new module can be imported by the name
    name, and uses the function initfunc as the initialization function called
    on the first attempted import.  This should be called before
    Py_Initialize()."""
    raise NotImplementedError

@cpython_api([_inittab], rffi.INT_real, error=-1)
def PyImport_ExtendInittab(space, newtab):
    """Add a collection of modules to the table of built-in modules.  The newtab
    array must end with a sentinel entry which contains NULL for the name
    field; failure to provide the sentinel value can result in a memory fault.
    Returns 0 on success or -1 if insufficient memory could be allocated to
    extend the internal table.  In the event of failure, no modules are added to the
    internal table.  This should be called before Py_Initialize()."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def Py_Initialize(space):
    """Initialize the Python interpreter.  In an application embedding Python,
    this should be called before using any other Python/C API functions; with
    the exception of Py_SetProgramName(), PyEval_InitThreads(),
    PyEval_ReleaseLock(), and PyEval_AcquireLock(). This initializes the table
    of loaded modules (sys.modules), and creates the fundamental modules
    __builtin__, __main__ and sys.  It also initializes the module search path
    (sys.path). It does not set sys.argv; use PySys_SetArgvEx() for that.  This
    is a no-op when called for a second time (without calling Py_Finalize()
    first).  There is no return value; it is a fatal error if the initialization
    fails."""
    raise NotImplementedError

@cpython_api([rffi.INT_real], lltype.Void)
def Py_InitializeEx(space, initsigs):
    """This function works like Py_Initialize() if initsigs is 1. If
    initsigs is 0, it skips initialization registration of signal handlers, which
    might be useful when Python is embedded.
    """
    raise NotImplementedError

@cpython_api([], lltype.Void)
def Py_Finalize(space):
    """Undo all initializations made by Py_Initialize() and subsequent use of
    Python/C API functions, and destroy all sub-interpreters (see
    Py_NewInterpreter() below) that were created and not yet destroyed since
    the last call to Py_Initialize().  Ideally, this frees all memory
    allocated by the Python interpreter.  This is a no-op when called for a second
    time (without calling Py_Initialize() again first).  There is no return
    value; errors during finalization are ignored.
    
    This function is provided for a number of reasons.  An embedding application
    might want to restart Python without having to restart the application itself.
    An application that has loaded the Python interpreter from a dynamically
    loadable library (or DLL) might want to free all memory allocated by Python
    before unloading the DLL. During a hunt for memory leaks in an application a
    developer might want to free all memory allocated by Python before exiting from
    the application.
    
    Bugs and caveats: The destruction of modules and objects in modules is done
    in random order; this may cause destructors (__del__() methods) to fail
    when they depend on other objects (even functions) or modules.  Dynamically
    loaded extension modules loaded by Python are not unloaded.  Small amounts of
    memory allocated by the Python interpreter may not be freed (if you find a leak,
    please report it).  Memory tied up in circular references between objects is not
    freed.  Some memory allocated by extension modules may not be freed.  Some
    extensions may not work properly if their initialization routine is called more
    than once; this can happen if an application calls Py_Initialize() and
    Py_Finalize() more than once."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], lltype.Void)
def Py_SetProgramName(space, name):
    """This function should be called before Py_Initialize() is called for the
    first time, if it is called at all.  It tells the interpreter the value of
    the argv[0] argument to the main() function of the program.  This is used by
    Py_GetPath() and some other functions below to find the Python run-time
    libraries relative to the interpreter executable.  The default value is
    'python'.  The argument should point to a zero-terminated character string
    in static storage whose contents will not change for the duration of the
    program's execution.  No code in the Python interpreter will change the
    contents of this storage."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetPrefix(space):
    """Return the prefix for installed platform-independent files. This is derived
    through a number of complicated rules from the program name set with
    Py_SetProgramName() and some environment variables; for example, if the
    program name is '/usr/local/bin/python', the prefix is '/usr/local'. The
    returned string points into static storage; the caller should not modify its
    value.  This corresponds to the prefix variable in the top-level
    Makefile and the --prefix argument to the configure
    script at build time.  The value is available to Python code as sys.prefix.
    It is only useful on Unix.  See also the next function."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetExecPrefix(space):
    """Return the exec-prefix for installed platform-dependent files.  This is
    derived through a number of complicated rules from the program name set with
    Py_SetProgramName() and some environment variables; for example, if the
    program name is '/usr/local/bin/python', the exec-prefix is
    '/usr/local'.  The returned string points into static storage; the caller
    should not modify its value.  This corresponds to the exec_prefix
    variable in the top-level Makefile and the --exec-prefix
    argument to the configure script at build  time.  The value is
    available to Python code as sys.exec_prefix.  It is only useful on Unix.
    
    Background: The exec-prefix differs from the prefix when platform dependent
    files (such as executables and shared libraries) are installed in a different
    directory tree.  In a typical installation, platform dependent files may be
    installed in the /usr/local/plat subtree while platform independent may
    be installed in /usr/local.
    
    Generally speaking, a platform is a combination of hardware and software
    families, e.g.  Sparc machines running the Solaris 2.x operating system are
    considered the same platform, but Intel machines running Solaris 2.x are another
    platform, and Intel machines running Linux are yet another platform.  Different
    major revisions of the same operating system generally also form different
    platforms.  Non-Unix operating systems are a different story; the installation
    strategies on those systems are so different that the prefix and exec-prefix are
    meaningless, and set to the empty string. Note that compiled Python bytecode
    files are platform independent (but not independent from the Python version by
    which they were compiled!).
    
    System administrators will know how to configure the mount or
    automount programs to share /usr/local between platforms
    while having /usr/local/plat be a different filesystem for each
    platform."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetProgramFullPath(space):
    """Return the full program name of the Python executable; this is computed
    as a side-effect of deriving the default module search path from the program
    name (set by Py_SetProgramName() above). The returned string points into
    static storage; the caller should not modify its value.  The value is
    available to Python code as sys.executable."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetPath(space):
    """Return the default module search path; this is computed from the program
    name (set by Py_SetProgramName() above) and some environment variables.  The
    returned string consists of a series of directory names separated by a
    platform dependent delimiter character.  The delimiter character is ':' on
    Unix and Mac OS X, ';' on Windows.  The returned string points into static
    storage; the caller should not modify its value.  The list sys.path is
    initialized with this value on interpreter startup; it can be (and usually
    is) modified later to change the search path for loading modules.
    
    XXX should give the exact rules"""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetVersion(space):
    """Return the version of this Python interpreter.  This is a string that looks
    something like
    
    "1.5 (\#67, Dec 31 1997, 22:34:28) [GCC 2.7.2.2]"
    
    The first word (up to the first space character) is the current Python version;
    the first three characters are the major and minor version separated by a
    period.  The returned string points into static storage; the caller should not
    modify its value.  The value is available to Python code as sys.version."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetPlatform(space):
    """Return the platform identifier for the current platform.  On Unix, this
    is formed from the"official" name of the operating system, converted to lower
    case, followed by the major revision number; e.g., for Solaris 2.x, which is
    also known as SunOS 5.x, the value is 'sunos5'.  On Mac OS X, it is
    'darwin'.  On Windows, it is 'win'.  The returned string points into
    static storage; the caller should not modify its value.  The value is available
    to Python code as sys.platform."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetCopyright(space):
    """Return the official copyright string for the current Python version, for example
    
    'Copyright 1991-1995 Stichting Mathematisch Centrum, Amsterdam'
    
    The returned string points into static storage; the caller should not modify its
    value.  The value is available to Python code as sys.copyright."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetCompiler(space):
    """Return an indication of the compiler used to build the current Python version,
    in square brackets, for example:
    
    "[GCC 2.7.2.2]"
    
    The returned string points into static storage; the caller should not modify its
    value.  The value is available to Python code as part of the variable
    sys.version."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetBuildInfo(space):
    """Return information about the sequence number and build date and time  of the
    current Python interpreter instance, for example
    
    "\#67, Aug  1 1997, 22:34:28"
    
    The returned string points into static storage; the caller should not modify its
    value.  The value is available to Python code as part of the variable
    sys.version."""
    raise NotImplementedError

@cpython_api([rffi.INT_real, rffi.CCHARPP, rffi.INT_real], lltype.Void)
def PySys_SetArgvEx(space, argc, argv, updatepath):
    """Set sys.argv based on argc and argv.  These parameters are similar to
    those passed to the program's main() function with the difference that the
    first entry should refer to the script file to be executed rather than the
    executable hosting the Python interpreter.  If there isn't a script that
    will be run, the first entry in argv can be an empty string.  If this
    function fails to initialize sys.argv, a fatal condition is signalled using
    Py_FatalError().
    
    If updatepath is zero, this is all the function does.  If updatepath
    is non-zero, the function also modifies sys.path according to the
    following algorithm:
    
    If the name of an existing script is passed in argv[0], the absolute
    path of the directory where the script is located is prepended to
    sys.path.
    
    Otherwise (that is, if argc is 0 or argv[0] doesn't point
    to an existing file name), an empty string is prepended to
    sys.path, which is the same as prepending the current working
    directory (".").
    
    It is recommended that applications embedding the Python interpreter
    for purposes other than executing a single script pass 0 as updatepath,
    and update sys.path themselves if desired.
    See CVE-2008-5983.
    
    On versions before 2.6.6, you can achieve the same effect by manually
    popping the first sys.path element after having called
    PySys_SetArgv(), for example using:
    
    PyRun_SimpleString("import sys; sys.path.pop(0)\n");
    
    XXX impl. doesn't seem consistent in allowing 0/NULL for the params;
    check w/ Guido."""
    raise NotImplementedError

@cpython_api([rffi.INT_real, rffi.CCHARPP], lltype.Void)
def PySys_SetArgv(space, argc, argv):
    """This function works like PySys_SetArgvEx() with updatepath set to 1."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], lltype.Void)
def Py_SetPythonHome(space, home):
    """Set the default "home" directory, that is, the location of the standard
    Python libraries.  See PYTHONHOME for the meaning of the
    argument string.
    
    The argument should point to a zero-terminated character string in static
    storage whose contents will not change for the duration of the program's
    execution.  No code in the Python interpreter will change the contents of
    this storage."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetPythonHome(space):
    """Return the default "home", that is, the value set by a previous call to
    Py_SetPythonHome(), or the value of the PYTHONHOME
    environment variable if it is set."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyEval_ReInitThreads(space):
    """This function is called from PyOS_AfterFork() to ensure that newly
    created child processes don't hold locks referring to threads which
    are not running in the child process."""
    raise NotImplementedError

@cpython_api([], PyInterpreterState)
def PyInterpreterState_New(space):
    """Create a new interpreter state object.  The global interpreter lock need not
    be held, but may be held if it is necessary to serialize calls to this
    function."""
    raise NotImplementedError

@cpython_api([PyInterpreterState], lltype.Void)
def PyInterpreterState_Clear(space, interp):
    """Reset all information in an interpreter state object.  The global interpreter
    lock must be held."""
    raise NotImplementedError

@cpython_api([PyInterpreterState], lltype.Void)
def PyInterpreterState_Delete(space, interp):
    """Destroy an interpreter state object.  The global interpreter lock need not be
    held.  The interpreter state must have been reset with a previous call to
    PyInterpreterState_Clear()."""
    raise NotImplementedError

@cpython_api([], PyObject)
def PyThreadState_GetDict(space):
    """Return a dictionary in which extensions can store thread-specific state
    information.  Each extension should use a unique key to use to store state in
    the dictionary.  It is okay to call this function when no current thread state
    is available. If this function returns NULL, no exception has been raised and
    the caller should assume no current thread state is available.
    
    Previously this could only be called when a current thread is active, and NULL
    meant that an exception was raised."""
    borrow_from()
    raise NotImplementedError

@cpython_api([lltype.Signed, PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyThreadState_SetAsyncExc(space, id, exc):
    """Asynchronously raise an exception in a thread. The id argument is the thread
    id of the target thread; exc is the exception object to be raised. This
    function does not steal any references to exc. To prevent naive misuse, you
    must write your own C extension to call this.  Must be called with the GIL held.
    Returns the number of thread states modified; this is normally one, but will be
    zero if the thread id isn't found.  If exc is NULL, the pending
    exception (if any) for the thread is cleared. This raises no exceptions.
    """
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyEval_AcquireLock(space):
    """Acquire the global interpreter lock.  The lock must have been created earlier.
    If this thread already has the lock, a deadlock ensues.
    
    This function does not change the current thread state.  Please use
    PyEval_RestoreThread() or PyEval_AcquireThread()
    instead."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyEval_ReleaseLock(space):
    """Release the global interpreter lock.  The lock must have been created earlier.
    
    This function does not change the current thread state.  Please use
    PyEval_SaveThread() or PyEval_ReleaseThread()
    instead."""
    raise NotImplementedError

@cpython_api([], PyThreadState)
def Py_NewInterpreter(space):
    """Create a new sub-interpreter.  This is an (almost) totally separate
    environment for the execution of Python code.  In particular, the new
    interpreter has separate, independent versions of all imported modules,
    including the fundamental modules builtins, __main__ and sys.  The table of
    loaded modules (sys.modules) and the module search path (sys.path) are also
    separate.  The new environment has no sys.argv variable.  It has new standard
    I/O stream file objects sys.stdin, sys.stdout and sys.stderr (however these
    refer to the same underlying file descriptors).
    
    The return value points to the first thread state created in the new
    sub-interpreter.  This thread state is made in the current thread state.
    Note that no actual thread is created; see the discussion of thread states
    below.  If creation of the new interpreter is unsuccessful, NULL is
    returned; no exception is set since the exception state is stored in the
    current thread state and there may not be a current thread state.  (Like all
    other Python/C API functions, the global interpreter lock must be held before
    calling this function and is still held when it returns; however, unlike most
    other Python/C API functions, there needn't be a current thread state on
    entry.)
    
    Extension modules are shared between (sub-)interpreters as follows: the first
    time a particular extension is imported, it is initialized normally, and a
    (shallow) copy of its module's dictionary is squirreled away.  When the same
    extension is imported by another (sub-)interpreter, a new module is initialized
    and filled with the contents of this copy; the extension's init function is
    not called.  Note that this is different from what happens when an extension is
    imported after the interpreter has been completely re-initialized by calling
    Py_Finalize() and Py_Initialize(); in that case, the extension's
    initmodule function is called again."""
    raise NotImplementedError

@cpython_api([PyThreadState], lltype.Void)
def Py_EndInterpreter(space, tstate):
    """Destroy the (sub-)interpreter represented by the given thread state. The
    given thread state must be the current thread state.  See the discussion of
    thread states below.  When the call returns, the current thread state is
    NULL.  All thread states associated with this interpreter are destroyed.
    (The global interpreter lock must be held before calling this function and is
    still held when it returns.)  Py_Finalize() will destroy all sub-interpreters
    that haven't been explicitly destroyed at that point."""
    raise NotImplementedError

@cpython_api([rffi.VOIDP], lltype.Void)
def Py_AddPendingCall(space, func):
    """Post a notification to the Python main thread.  If successful, func will
    be called with the argument arg at the earliest convenience.  func will be
    called having the global interpreter lock held and can thus use the full
    Python API and can take any action such as setting object attributes to
    signal IO completion.  It must return 0 on success, or -1 signalling an
    exception.  The notification function won't be interrupted to perform another
    asynchronous notification recursively, but it can still be interrupted to
    switch threads if the global interpreter lock is released, for example, if it
    calls back into Python code.
    
    This function returns 0 on success in which case the notification has been
    scheduled.  Otherwise, for example if the notification buffer is full, it
    returns -1 without setting any exception.
    
    This function can be called on any thread, be it a Python thread or some
    other system thread.  If it is a Python thread, it doesn't matter if it holds
    the global interpreter lock or not.
    """
    raise NotImplementedError

@cpython_api([Py_tracefunc, PyObject], lltype.Void)
def PyEval_SetProfile(space, func, obj):
    """Set the profiler function to func.  The obj parameter is passed to the
    function as its first parameter, and may be any Python object, or NULL.  If
    the profile function needs to maintain state, using a different value for obj
    for each thread provides a convenient and thread-safe place to store it.  The
    profile function is called for all monitored events except the line-number
    events."""
    raise NotImplementedError

@cpython_api([Py_tracefunc, PyObject], lltype.Void)
def PyEval_SetTrace(space, func, obj):
    """Set the tracing function to func.  This is similar to
    PyEval_SetProfile(), except the tracing function does receive line-number
    events."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyEval_GetCallStats(space, self):
    """Return a tuple of function call counts.  There are constants defined for the
    positions within the tuple:
    
    Name
    
    Value
    
    PCALL_ALL
    
    0
    
    PCALL_FUNCTION
    
    1
    
    PCALL_FAST_FUNCTION
    
    2
    
    PCALL_FASTER_FUNCTION
    
    3
    
    PCALL_METHOD
    
    4
    
    PCALL_BOUND_METHOD
    
    5
    
    PCALL_CFUNCTION
    
    6
    
    PCALL_TYPE
    
    7
    
    PCALL_GENERATOR
    
    8
    
    PCALL_OTHER
    
    9
    
    PCALL_POP
    
    10
    
    PCALL_FAST_FUNCTION means no argument tuple needs to be created.
    PCALL_FASTER_FUNCTION means that the fast-path frame setup code is used.
    
    If there is a method call where the call can be optimized by changing
    the argument tuple and calling the function directly, it gets recorded
    twice.
    
    This function is only present if Python is compiled with CALL_PROFILE
    defined."""
    raise NotImplementedError

@cpython_api([PyInterpreterState], PyThreadState)
def PyInterpreterState_ThreadHead(space, interp):
    """Return the a pointer to the first PyThreadState object in the list of
    threads associated with the interpreter interp.
    """
    raise NotImplementedError

@cpython_api([PyThreadState], PyThreadState)
def PyThreadState_Next(space, tstate):
    """Return the next thread state object after tstate from the list of all such
    objects belonging to the same PyInterpreterState object.
    """
    raise NotImplementedError

@cpython_api([rffi.SIZE_T], PyObject)
def PyInt_FromSize_t(space, ival):
    """Create a new integer object with a value of ival. If the value exceeds
    LONG_MAX, a long integer object is returned.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.ULONGLONG, error=-1)
def PyInt_AsUnsignedLongLongMask(space, io):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    unsigned long long, without checking for overflow.
    """
    raise NotImplementedError

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def PyInt_ClearFreeList(space):
    """Clear the integer free list. Return the number of items that could not
    be freed.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PySeqIter_Check(space, op):
    """Return true if the type of op is PySeqIter_Type.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyCallIter_Check(space, op):
    """Return true if the type of op is PyCallIter_Type.
    """
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PyList_GetSlice(space, list, low, high):
    """Return a list of the objects in list containing the objects between low
    and high.  Return NULL and set an exception if unsuccessful.  Analogous
    to list[low:high].  Negative indices, as when slicing from Python, are not
    supported.
    
    This function used an int for low and high. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([Py_ssize_t], PyObject)
def PyLong_FromSsize_t(space, v):
    """Return a new PyLongObject object from a C Py_ssize_t, or
    NULL on failure.
    """
    raise NotImplementedError

@cpython_api([rffi.SIZE_T], PyObject)
def PyLong_FromSize_t(space, v):
    """Return a new PyLongObject object from a C size_t, or
    NULL on failure.
    """
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t, rffi.INT_real], PyObject)
def PyLong_FromUnicode(space, u, length, base):
    """Convert a sequence of Unicode digits to a Python long integer value.  The first
    parameter, u, points to the first character of the Unicode string, length
    gives the number of characters, and base is the radix for the conversion.  The
    radix must be in the range [2, 36]; if it is out of range, ValueError
    will be raised.
    
    This function used an int for length. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyLong_AsSsize_t(space, pylong):
    """Return a C Py_ssize_t representation of the contents of pylong.  If
    pylong is greater than PY_SSIZE_T_MAX, an OverflowError is raised
    and -1 will be returned.
    """
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real, error=-1)
def PyMapping_DelItemString(space, o, key):
    """Remove the mapping for object key from the object o. Return -1 on
    failure.  This is equivalent to the Python statement del o[key]."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyMapping_DelItem(space, o, key):
    """Remove the mapping for object key from the object o. Return -1 on
    failure.  This is equivalent to the Python statement del o[key]."""
    raise NotImplementedError

@cpython_api([lltype.Signed, FILE, rffi.INT_real], lltype.Void)
def PyMarshal_WriteLongToFile(space, value, file, version):
    """Marshal a long integer, value, to file.  This will only write
    the least-significant 32 bits of value; regardless of the size of the
    native long type.
    
    version indicates the file format."""
    raise NotImplementedError

@cpython_api([PyObject, FILE, rffi.INT_real], lltype.Void)
def PyMarshal_WriteObjectToFile(space, value, file, version):
    """Marshal a Python object, value, to file.
    
    version indicates the file format."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyMarshal_WriteObjectToString(space, value, version):
    """Return a string object containing the marshalled representation of value.
    
    version indicates the file format."""
    raise NotImplementedError

@cpython_api([FILE], lltype.Signed, error=CANNOT_FAIL)
def PyMarshal_ReadLongFromFile(space, file):
    """Return a C long from the data stream in a FILE* opened
    for reading.  Only a 32-bit value can be read in using this function,
    regardless of the native size of long."""
    raise NotImplementedError

@cpython_api([FILE], rffi.INT_real, error=CANNOT_FAIL)
def PyMarshal_ReadShortFromFile(space, file):
    """Return a C short from the data stream in a FILE* opened
    for reading.  Only a 16-bit value can be read in using this function,
    regardless of the native size of short."""
    raise NotImplementedError

@cpython_api([FILE], PyObject)
def PyMarshal_ReadObjectFromFile(space, file):
    """Return a Python object from the data stream in a FILE* opened for
    reading.  On error, sets the appropriate exception (EOFError or
    TypeError) and returns NULL."""
    raise NotImplementedError

@cpython_api([FILE], PyObject)
def PyMarshal_ReadLastObjectFromFile(space, file):
    """Return a Python object from the data stream in a FILE* opened for
    reading.  Unlike PyMarshal_ReadObjectFromFile(), this function
    assumes that no further objects will be read from the file, allowing it to
    aggressively load file data into memory so that the de-serialization can
    operate from data in memory rather than reading a byte at a time from the
    file.  Only use these variant if you are certain that you won't be reading
    anything else from the file.  On error, sets the appropriate exception
    (EOFError or TypeError) and returns NULL."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t], PyObject)
def PyMarshal_ReadObjectFromString(space, string, len):
    """Return a Python object from the data stream in a character buffer
    containing len bytes pointed to by string.  On error, sets the
    appropriate exception (EOFError or TypeError) and returns
    NULL.
    
    This function used an int type for len. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def PyMethod_ClearFreeList(space):
    """Clear the free list. Return the total number of freed items.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyModule_CheckExact(space, p):
    """Return true if p is a module object, but not a subtype of
    PyModule_Type.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP], PyObject)
def PyModule_New(space, name):
    """Return a new module object with the __name__ attribute set to name.  Only
    the module's __doc__ and __name__ attributes are filled in; the caller is
    responsible for providing a __file__ attribute."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyModule_GetFilename(space, module):
    """Return the name of the file from which module was loaded using module's
    __file__ attribute.  If this is not defined, or if it is not a string, raise
    SystemError and return NULL."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT], rffi.INT_real, error=-1)
def PyModule_AddIntMacro(space, module, macro):
    """Add an int constant to module. The name and the value are taken from
    macro. For example PyModule_AddConstant(module, AF_INET) adds the int
    constant AF_INET with the value of AF_INET to module.
    Return -1 on error, 0 on success.
    """
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real, error=-1)
def PyModule_AddStringMacro(space, module, macro):
    """Add a string constant to module.
    """
    raise NotImplementedError

@cpython_api([PyObjectP, PyObjectP], rffi.INT_real, error=-1)
def PyNumber_Coerce(space, p1, p2):
    """This function takes the addresses of two variables of type PyObject*.  If
    the objects pointed to by *p1 and *p2 have the same type, increment their
    reference count and return 0 (success). If the objects can be converted to a
    common numeric type, replace *p1 and *p2 by their converted value (with
    'new' reference counts), and return 0. If no conversion is possible, or if
    some other error occurs, return -1 (failure) and don't increment the
    reference counts.  The call PyNumber_Coerce(&o1, &o2) is equivalent to the
    Python statement o1, o2 = coerce(o1, o2)."""
    raise NotImplementedError

@cpython_api([PyObjectP, PyObjectP], rffi.INT_real, error=-1)
def PyNumber_CoerceEx(space, p1, p2):
    """This function is similar to PyNumber_Coerce(), except that it returns
    1 when the conversion is not possible and when no error is raised.
    Reference counts are still not increased in this case."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyNumber_Index(space, o):
    """Returns the o converted to a Python int or long on success or NULL with a
    TypeError exception raised on failure.
    """
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyNumber_ToBase(space, n, base):
    """Returns the integer n converted to base as a string with a base
    marker of '0b', '0o', or '0x' if applicable.  When
    base is not 2, 8, 10, or 16, the format is 'x#num' where x is the
    base. If n is not an int object, it is converted with
    PyNumber_Index() first.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyObject_Bytes(space, o):
    """Compute a bytes representation of object o.  In 2.x, this is just a alias
    for PyObject_Str()."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Signed, error=-1)
def PyObject_HashNotImplemented(space, o):
    """Set a TypeError indicating that type(o) is not hashable and return -1.
    This function receives special treatment when stored in a tp_hash slot,
    allowing a type to explicitly indicate to the interpreter that it is not
    hashable.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyObject_Dir(space, o):
    """This is equivalent to the Python expression dir(o), returning a (possibly
    empty) list of strings appropriate for the object argument, or NULL if there
    was an error.  If the argument is NULL, this is like the Python dir(),
    returning the names of the current locals; in this case, if no execution frame
    is active then NULL is returned but PyErr_Occurred() will return false."""
    raise NotImplementedError

@cpython_api([], PyFrameObject)
def PyEval_GetFrame(space):
    """Return the current thread state's frame, which is NULL if no frame is
    currently executing."""
    borrow_from()
    raise NotImplementedError

@cpython_api([PyFrameObject], rffi.INT_real, error=CANNOT_FAIL)
def PyFrame_GetLineNumber(space, frame):
    """Return the line number that frame is currently executing."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def PyEval_GetRestricted(space):
    """If there is a current frame and it is executing in restricted mode, return true,
    otherwise false."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyEval_GetFuncName(space, func):
    """Return the name of func if it is a function, class or instance object, else the
    name of funcs type."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyEval_GetFuncDesc(space, func):
    """Return a description string, depending on the type of func.
    Return values include "()" for functions and methods, " constructor",
    " instance", and " object".  Concatenated with the result of
    PyEval_GetFuncName(), the result will be a description of
    func."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PySequence_InPlaceConcat(space, o1, o2):
    """Return the concatenation of o1 and o2 on success, and NULL on failure.
    The operation is done in-place when o1 supports it.  This is the equivalent
    of the Python expression o1 += o2."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PySequence_InPlaceRepeat(space, o, count):
    """Return the result of repeating sequence object o count times, or NULL on
    failure.  The operation is done in-place when o supports it.  This is the
    equivalent of the Python expression o *= count.
    
    This function used an int type for count. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], Py_ssize_t, error=-1)
def PySequence_Count(space, o, value):
    """Return the number of occurrences of value in o, that is, return the number
    of keys for which o[key] == value.  On failure, return -1.  This is
    equivalent to the Python expression o.count(value).
    
    This function returned an int type. This might require changes
    in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], Py_ssize_t, error=-1)
def PySequence_Index(space, o, value):
    """Return the first index i for which o[i] == value.  On error, return
    -1.    This is equivalent to the Python expression o.index(value).
    
    This function returned an int type. This might require changes
    in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObjectP)
def PySequence_Fast_ITEMS(space, o):
    """Return the underlying array of PyObject pointers.  Assumes that o was returned
    by PySequence_Fast() and o is not NULL.
    
    Note, if a list gets resized, the reallocation may relocate the items array.
    So, only use the underlying array pointer in contexts where the sequence
    cannot change.
    """
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PySequence_ITEM(space, o, i):
    """Return the ith element of o or NULL on failure. Macro form of
    PySequence_GetItem() but without checking that
    PySequence_Check(o)() is true and without adjustment for negative
    indices.
    
    This function used an int type for i. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PySet_Check(space, p):
    """Return true if p is a set object or an instance of a subtype.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyFrozenSet_Check(space, p):
    """Return true if p is a frozenset object or an instance of a
    subtype.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyAnySet_Check(space, p):
    """Return true if p is a set object, a frozenset object, or an
    instance of a subtype."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyAnySet_CheckExact(space, p):
    """Return true if p is a set object or a frozenset object but
    not an instance of a subtype."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyFrozenSet_CheckExact(space, p):
    """Return true if p is a frozenset object but not an instance of a
    subtype."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PySet_New(space, iterable):
    """Return a new set containing objects returned by the iterable.  The
    iterable may be NULL to create a new empty set.  Return the new set on
    success or NULL on failure.  Raise TypeError if iterable is not
    actually iterable.  The constructor is also useful for copying a set
    (c=set(s))."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyFrozenSet_New(space, iterable):
    """Return a new frozenset containing objects returned by the iterable.
    The iterable may be NULL to create a new empty frozenset.  Return the new
    set on success or NULL on failure.  Raise TypeError if iterable is
    not actually iterable.
    
    Now guaranteed to return a brand-new frozenset.  Formerly,
    frozensets of zero-length were a singleton.  This got in the way of
    building-up new frozensets with PySet_Add()."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PySet_Size(space, anyset):
    """Return the length of a set or frozenset object. Equivalent to
    len(anyset).  Raises a PyExc_SystemError if anyset is not a set, frozenset,
    or an instance of a subtype.
    
    This function returned an int. This might require changes in
    your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PySet_GET_SIZE(space, anyset):
    """Macro form of PySet_Size() without error checking."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PySet_Contains(space, anyset, key):
    """Return 1 if found, 0 if not found, and -1 if an error is encountered.  Unlike
    the Python __contains__() method, this function does not automatically
    convert unhashable sets into temporary frozensets.  Raise a TypeError if
    the key is unhashable. Raise PyExc_SystemError if anyset is not a
    set, frozenset, or an instance of a subtype."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PySet_Add(space, set, key):
    """Add key to a set instance.  Does not apply to frozenset
    instances.  Return 0 on success or -1 on failure. Raise a TypeError if
    the key is unhashable. Raise a MemoryError if there is no room to grow.
    Raise a SystemError if set is an not an instance of set or its
    subtype.
    
    Now works with instances of frozenset or its subtypes.
    Like PyTuple_SetItem() in that it can be used to fill-in the
    values of brand new frozensets before they are exposed to other code."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PySet_Discard(space, set, key):
    """Return 1 if found and removed, 0 if not found (no action taken), and -1 if an
    error is encountered.  Does not raise KeyError for missing keys.  Raise a
    TypeError if the key is unhashable.  Unlike the Python discard()
    method, this function does not automatically convert unhashable sets into
    temporary frozensets. Raise PyExc_SystemError if set is an not an
    instance of set or its subtype."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PySet_Pop(space, set):
    """Return a new reference to an arbitrary object in the set, and removes the
    object from the set.  Return NULL on failure.  Raise KeyError if the
    set is empty. Raise a SystemError if set is an not an instance of
    set or its subtype."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PySet_Clear(space, set):
    """Empty an existing set of all elements."""
    raise NotImplementedError

@cpython_api([PyObjectP], lltype.Void)
def PyString_InternInPlace(space, string):
    """Intern the argument *string in place.  The argument must be the address of a
    pointer variable pointing to a Python string object.  If there is an existing
    interned string that is the same as *string, it sets *string to it
    (decrementing the reference count of the old string object and incrementing the
    reference count of the interned string object), otherwise it leaves *string
    alone and interns it (incrementing its reference count).  (Clarification: even
    though there is a lot of talk about reference counts, think of this function as
    reference-count-neutral; you own the object after the call if and only if you
    owned it before the call.)
    
    This function is not available in 3.x and does not have a PyBytes alias."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyString_Decode(space, s, size, encoding, errors):
    """Create an object by decoding size bytes of the encoded buffer s using the
    codec registered for encoding.  encoding and errors have the same meaning
    as the parameters of the same name in the unicode() built-in function.
    The codec to be used is looked up using the Python codec registry.  Return
    NULL if an exception was raised by the codec.
    
    This function is not available in 3.x and does not have a PyBytes alias.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyString_AsDecodedObject(space, str, encoding, errors):
    """Decode a string object by passing it to the codec registered for encoding and
    return the result as Python object. encoding and errors have the same
    meaning as the parameters of the same name in the string encode() method.
    The codec to be used is looked up using the Python codec registry. Return NULL
    if an exception was raised by the codec.
    
    This function is not available in 3.x and does not have a PyBytes alias."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyString_Encode(space, s, size, encoding, errors):
    """Encode the char buffer of the given size by passing it to the codec
    registered for encoding and return a Python object. encoding and errors
    have the same meaning as the parameters of the same name in the string
    encode() method. The codec to be used is looked up using the Python codec
    registry.  Return NULL if an exception was raised by the codec.
    
    This function is not available in 3.x and does not have a PyBytes alias.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP], rffi.INT_real, error=CANNOT_FAIL)
def Py_FdIsInteractive(space, fp, filename):
    """Return true (nonzero) if the standard I/O file fp with name filename is
    deemed interactive.  This is the case for files for which isatty(fileno(fp))
    is true.  If the global flag Py_InteractiveFlag is true, this function
    also returns true if the filename pointer is NULL or if the name is equal to
    one of the strings '<stdin>' or '???'."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyOS_AfterFork(space):
    """Function to update some internal state after a process fork; this should be
    called in the new process if the Python interpreter will continue to be used.
    If a new executable is loaded into the new process, this function does not need
    to be called."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def PyOS_CheckStack(space):
    """Return true when the interpreter runs out of stack space.  This is a reliable
    check, but is only available when USE_STACKCHECK is defined (currently
    on Windows using the Microsoft Visual C++ compiler).  USE_STACKCHECK
    will be defined automatically; you should never change the definition in your
    own code."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, FILE], FILE)
def PySys_GetFile(space, name, default):
    """Return the FILE* associated with the object name in the
    sys module, or def if name is not in the module or is not associated
    with a FILE*."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PySys_ResetWarnOptions(space):
    """Reset sys.warnoptions to an empty list."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], lltype.Void)
def PySys_AddWarnOption(space, s):
    """Append s to sys.warnoptions."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], lltype.Void)
def PySys_SetPath(space, path):
    """Set sys.path to a list object of paths found in path which should
    be a list of paths separated with the platform's search path delimiter
    (: on Unix, ; on Windows)."""
    raise NotImplementedError

@cpython_api([rffi.INT_real], lltype.Void)
def Py_Exit(space, status):
    """Exit the current process.  This calls Py_Finalize() and then calls the
    standard C library function exit(status)."""
    raise NotImplementedError

@cpython_api([rffi.VOIDP], rffi.INT_real, error=-1)
def Py_AtExit(space, func):
    """Register a cleanup function to be called by Py_Finalize().  The cleanup
    function will be called with no arguments and should return no value.  At
    most 32 cleanup functions can be registered.  When the registration is
    successful, Py_AtExit() returns 0; on failure, it returns -1.  The cleanup
    function registered last is called first. Each cleanup function will be
    called at most once.  Since Python's internal finalization will have
    completed before the cleanup function, no Python APIs should be called by
    func."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PyTuple_GetSlice(space, p, low, high):
    """Take a slice of the tuple pointed to by p from low to high and return it
    as a new tuple.
    
    This function used an int type for low and high. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def PyTuple_ClearFreeList(space):
    """Clear the free list. Return the total number of freed items.
    """
    raise NotImplementedError

@cpython_api([], rffi.UINT, error=CANNOT_FAIL)
def PyType_ClearCache(space):
    """Clear the internal lookup cache. Return the current version tag.
    """
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr], lltype.Void)
def PyType_Modified(space, type):
    """Invalidate the internal lookup cache for the type and all of its
    subtypes.  This function must be called after any manual
    modification of the attributes or base classes of the type.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyType_IS_GC(space, o):
    """Return true if the type object includes support for the cycle detector; this
    tests the type flag Py_TPFLAGS_HAVE_GC.
    """
    raise NotImplementedError

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def PyUnicode_ClearFreeList(space):
    """Clear the free list. Return the total number of freed items.
    """
    raise NotImplementedError

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISTITLE(space, ch):
    """Return 1 or 0 depending on whether ch is a titlecase character."""
    raise NotImplementedError

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISDIGIT(space, ch):
    """Return 1 or 0 depending on whether ch is a digit character."""
    raise NotImplementedError

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISNUMERIC(space, ch):
    """Return 1 or 0 depending on whether ch is a numeric character."""
    raise NotImplementedError

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISALPHA(space, ch):
    """Return 1 or 0 depending on whether ch is an alphabetic character."""
    raise NotImplementedError

@cpython_api([Py_UNICODE], Py_UNICODE, error=CANNOT_FAIL)
def Py_UNICODE_TOTITLE(space, ch):
    """Return the character ch converted to title case."""
    raise NotImplementedError

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_TODECIMAL(space, ch):
    """Return the character ch converted to a decimal positive integer.  Return
    -1 if this is not possible.  This macro does not raise exceptions."""
    raise NotImplementedError

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_TODIGIT(space, ch):
    """Return the character ch converted to a single digit integer. Return -1 if
    this is not possible.  This macro does not raise exceptions."""
    raise NotImplementedError

@cpython_api([Py_UNICODE], rffi.DOUBLE, error=CANNOT_FAIL)
def Py_UNICODE_TONUMERIC(space, ch):
    """Return the character ch converted to a double. Return -1.0 if this is not
    possible.  This macro does not raise exceptions."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], PyObject)
def PyUnicode_FromFormat(space, format):
    """Take a C printf()-style format string and a variable number of
    arguments, calculate the size of the resulting Python unicode string and return
    a string with the values formatted into it.  The variable arguments must be C
    types and must correspond exactly to the format characters in the format
    string.  The following format characters are allowed:
    
    Format Characters
    
    Type
    
    Comment
    
    %%
    
    n/a
    
    The literal % character.
    
    %c
    
    int
    
    A single character,
    represented as an C int.
    
    %d
    
    int
    
    Exactly equivalent to
    printf("%d").
    
    %u
    
    unsigned int
    
    Exactly equivalent to
    printf("%u").
    
    %ld
    
    long
    
    Exactly equivalent to
    printf("%ld").
    
    %lu
    
    unsigned long
    
    Exactly equivalent to
    printf("%lu").
    
    %zd
    
    Py_ssize_t
    
    Exactly equivalent to
    printf("%zd").
    
    %zu
    
    size_t
    
    Exactly equivalent to
    printf("%zu").
    
    %i
    
    int
    
    Exactly equivalent to
    printf("%i").
    
    %x
    
    int
    
    Exactly equivalent to
    printf("%x").
    
    %s
    
    char*
    
    A null-terminated C character
    array.
    
    %p
    
    void*
    
    The hex representation of a C
    pointer. Mostly equivalent to
    printf("%p") except that
    it is guaranteed to start with
    the literal 0x regardless
    of what the platform's
    printf yields.
    
    %U
    
    PyObject*
    
    A unicode object.
    
    %V
    
    PyObject*, char *
    
    A unicode object (which may be
    NULL) and a null-terminated
    C character array as a second
    parameter (which will be used,
    if the first parameter is
    NULL).
    
    %S
    
    PyObject*
    
    The result of calling
    PyObject_Unicode().
    
    %R
    
    PyObject*
    
    The result of calling
    PyObject_Repr().
    
    An unrecognized format character causes all the rest of the format string to be
    copied as-is to the result string, and any extra arguments discarded.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, va_list], PyObject)
def PyUnicode_FromFormatV(space, format, vargs):
    """Identical to PyUnicode_FromFormat() except that it takes exactly two
    arguments.
    """
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyUnicode_Encode(space, s, size, encoding, errors):
    """Encode the Py_UNICODE buffer of the given size and return a Python
    string object.  encoding and errors have the same meaning as the parameters
    of the same name in the Unicode encode() method.  The codec to be used is
    looked up using the Python codec registry.  Return NULL if an exception was
    raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, Py_ssize_t], PyObject)
def PyUnicode_DecodeUTF8Stateful(space, s, size, errors, consumed):
    """If consumed is NULL, behave like PyUnicode_DecodeUTF8(). If
    consumed is not NULL, trailing incomplete UTF-8 byte sequences will not be
    treated as an error. Those bytes will not be decoded and the number of bytes
    that have been decoded will be stored in consumed.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_EncodeUTF8(space, s, size, errors):
    """Encode the Py_UNICODE buffer of the given size using UTF-8 and return a
    Python string object.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, rffi.INTP], PyObject)
def PyUnicode_DecodeUTF32(space, s, size, errors, byteorder):
    """Decode length bytes from a UTF-32 encoded buffer string and return the
    corresponding Unicode object.  errors (if non-NULL) defines the error
    handling. It defaults to "strict".
    
    If byteorder is non-NULL, the decoder starts decoding using the given byte
    order:
    
    *byteorder == -1: little endian
    *byteorder == 0:  native order
    *byteorder == 1:  big endian
    
    If *byteorder is zero, and the first four bytes of the input data are a
    byte order mark (BOM), the decoder switches to this byte order and the BOM is
    not copied into the resulting Unicode string.  If *byteorder is -1 or
    1, any byte order mark is copied to the output.
    
    After completion, *byteorder is set to the current byte order at the end
    of input data.
    
    In a narrow build codepoints outside the BMP will be decoded as surrogate pairs.
    
    If byteorder is NULL, the codec starts in native order mode.
    
    Return NULL if an exception was raised by the codec.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, rffi.INTP, Py_ssize_t], PyObject)
def PyUnicode_DecodeUTF32Stateful(space, s, size, errors, byteorder, consumed):
    """If consumed is NULL, behave like PyUnicode_DecodeUTF32(). If
    consumed is not NULL, PyUnicode_DecodeUTF32Stateful() will not treat
    trailing incomplete UTF-32 byte sequences (such as a number of bytes not divisible
    by four) as an error. Those bytes will not be decoded and the number of bytes
    that have been decoded will be stored in consumed.
    """
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t, rffi.CCHARP, rffi.INT_real], PyObject)
def PyUnicode_EncodeUTF32(space, s, size, errors, byteorder):
    """Return a Python bytes object holding the UTF-32 encoded value of the Unicode
    data in s.  Output is written according to the following byte order:
    
    byteorder == -1: little endian
    byteorder == 0:  native byte order (writes a BOM mark)
    byteorder == 1:  big endian
    
    If byteorder is 0, the output string will always start with the Unicode BOM
    mark (U+FEFF). In the other two modes, no BOM mark is prepended.
    
    If Py_UNICODE_WIDE is not defined, surrogate pairs will be output
    as a single codepoint.
    
    Return NULL if an exception was raised by the codec.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsUTF32String(space, unicode):
    """Return a Python string using the UTF-32 encoding in native byte order. The
    string always starts with a BOM mark.  Error handling is "strict".  Return
    NULL if an exception was raised by the codec.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, rffi.INTP, Py_ssize_t], PyObject)
def PyUnicode_DecodeUTF16Stateful(space, s, size, errors, byteorder, consumed):
    """If consumed is NULL, behave like PyUnicode_DecodeUTF16(). If
    consumed is not NULL, PyUnicode_DecodeUTF16Stateful() will not treat
    trailing incomplete UTF-16 byte sequences (such as an odd number of bytes or a
    split surrogate pair) as an error. Those bytes will not be decoded and the
    number of bytes that have been decoded will be stored in consumed.
    
    This function used an int type for size and an int *
    type for consumed. This might require changes in your code for
    properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t, rffi.CCHARP, rffi.INT_real], PyObject)
def PyUnicode_EncodeUTF16(space, s, size, errors, byteorder):
    """Return a Python string object holding the UTF-16 encoded value of the Unicode
    data in s.  Output is written according to the following byte order:
    
    byteorder == -1: little endian
    byteorder == 0:  native byte order (writes a BOM mark)
    byteorder == 1:  big endian
    
    If byteorder is 0, the output string will always start with the Unicode BOM
    mark (U+FEFF). In the other two modes, no BOM mark is prepended.
    
    If Py_UNICODE_WIDE is defined, a single Py_UNICODE value may get
    represented as a surrogate pair. If it is not defined, each Py_UNICODE
    values is interpreted as an UCS-2 character.
    
    Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsUTF16String(space, unicode):
    """Return a Python string using the UTF-16 encoding in native byte order. The
    string always starts with a BOM mark.  Error handling is "strict".  Return
    NULL if an exception was raised by the codec."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_DecodeUTF7(space, s, size, errors):
    """Create a Unicode object by decoding size bytes of the UTF-7 encoded string
    s.  Return NULL if an exception was raised by the codec."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, Py_ssize_t], PyObject)
def PyUnicode_DecodeUTF7Stateful(space, s, size, errors, consumed):
    """If consumed is NULL, behave like PyUnicode_DecodeUTF7().  If
    consumed is not NULL, trailing incomplete UTF-7 base-64 sections will not
    be treated as an error.  Those bytes will not be decoded and the number of
    bytes that have been decoded will be stored in consumed."""
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t, rffi.INT_real, rffi.INT_real, rffi.CCHARP], PyObject)
def PyUnicode_EncodeUTF7(space, s, size, base64SetO, base64WhiteSpace, errors):
    """Encode the Py_UNICODE buffer of the given size using UTF-7 and
    return a Python bytes object.  Return NULL if an exception was raised by
    the codec.
    
    If base64SetO is nonzero, "Set O" (punctuation that has no otherwise
    special meaning) will be encoded in base-64.  If base64WhiteSpace is
    nonzero, whitespace will be encoded in base-64.  Both are set to zero for the
    Python "utf-7" codec."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_DecodeUnicodeEscape(space, s, size, errors):
    """Create a Unicode object by decoding size bytes of the Unicode-Escape encoded
    string s.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t], PyObject)
def PyUnicode_EncodeUnicodeEscape(space, s, size):
    """Encode the Py_UNICODE buffer of the given size using Unicode-Escape and
    return a Python string object.  Return NULL if an exception was raised by the
    codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_DecodeRawUnicodeEscape(space, s, size, errors):
    """Create a Unicode object by decoding size bytes of the Raw-Unicode-Escape
    encoded string s.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_EncodeRawUnicodeEscape(space, s, size, errors):
    """Encode the Py_UNICODE buffer of the given size using Raw-Unicode-Escape
    and return a Python string object.  Return NULL if an exception was raised by
    the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsRawUnicodeEscapeString(space, unicode):
    """Encode a Unicode object using Raw-Unicode-Escape and return the result as
    Python string object. Error handling is "strict". Return NULL if an exception
    was raised by the codec."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_DecodeLatin1(space, s, size, errors):
    """Create a Unicode object by decoding size bytes of the Latin-1 encoded string
    s.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_EncodeLatin1(space, s, size, errors):
    """Encode the Py_UNICODE buffer of the given size using Latin-1 and return
    a Python string object.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsLatin1String(space, unicode):
    """Encode a Unicode object using Latin-1 and return the result as Python string
    object.  Error handling is "strict".  Return NULL if an exception was raised
    by the codec."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, PyObject, rffi.CCHARP], PyObject)
def PyUnicode_DecodeCharmap(space, s, size, mapping, errors):
    """Create a Unicode object by decoding size bytes of the encoded string s using
    the given mapping object.  Return NULL if an exception was raised by the
    codec. If mapping is NULL latin-1 decoding will be done. Else it can be a
    dictionary mapping byte or a unicode string, which is treated as a lookup table.
    Byte values greater that the length of the string and U+FFFE "characters" are
    treated as "undefined mapping".
    
    Allowed unicode string as mapping argument.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t, PyObject, rffi.CCHARP], PyObject)
def PyUnicode_EncodeCharmap(space, s, size, mapping, errors):
    """Encode the Py_UNICODE buffer of the given size using the given
    mapping object and return a Python string object. Return NULL if an
    exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_AsCharmapString(space, unicode, mapping):
    """Encode a Unicode object using the given mapping object and return the result
    as Python string object.  Error handling is "strict".  Return NULL if an
    exception was raised by the codec."""
    raise NotImplementedError

@cpython_api([rffi.CWCHARP, Py_ssize_t, PyObject, rffi.CCHARP], PyObject)
def PyUnicode_TranslateCharmap(space, s, size, table, errors):
    """Translate a Py_UNICODE buffer of the given length by applying a
    character mapping table to it and return the resulting Unicode object.  Return
    NULL when an exception was raised by the codec.
    
    The mapping table must map Unicode ordinal integers to Unicode ordinal
    integers or None (causing deletion of the character).
    
    Mapping tables need only provide the __getitem__() interface; dictionaries
    and sequences work well.  Unmapped character ordinals (ones which cause a
    LookupError) are left untouched and are copied as-is.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.INT_real, rffi.CCHARP, rffi.INTP], PyObject)
def PyUnicode_DecodeMBCSStateful(space, s, size, errors, consumed):
    """If consumed is NULL, behave like PyUnicode_DecodeMBCS(). If
    consumed is not NULL, PyUnicode_DecodeMBCSStateful() will not decode
    trailing lead byte and the number of bytes that have been decoded will be stored
    in consumed.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsMBCSString(space, unicode):
    """Encode a Unicode object using MBCS and return the result as Python string
    object.  Error handling is "strict".  Return NULL if an exception was raised
    by the codec."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_Concat(space, left, right):
    """Concat two strings giving a new Unicode string."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, Py_ssize_t], PyObject)
def PyUnicode_Split(space, s, sep, maxsplit):
    """Split a string giving a list of Unicode strings.  If sep is NULL, splitting
    will be done at all whitespace substrings.  Otherwise, splits occur at the given
    separator.  At most maxsplit splits will be done.  If negative, no limit is
    set.  Separators are not included in the resulting list.
    
    This function used an int type for maxsplit. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyUnicode_Splitlines(space, s, keepend):
    """Split a Unicode string at line breaks, returning a list of Unicode strings.
    CRLF is considered to be one line break.  If keepend is 0, the Line break
    characters are not included in the resulting strings."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.CCHARP], PyObject)
def PyUnicode_Translate(space, str, table, errors):
    """Translate a string by applying a character mapping table to it and return the
    resulting Unicode object.
    
    The mapping table must map Unicode ordinal integers to Unicode ordinal integers
    or None (causing deletion of the character).
    
    Mapping tables need only provide the __getitem__() interface; dictionaries
    and sequences work well.  Unmapped character ordinals (ones which cause a
    LookupError) are left untouched and are copied as-is.
    
    errors has the usual meaning for codecs. It may be NULL which indicates to
    use the default error handling."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_Join(space, separator, seq):
    """Join a sequence of strings using the given separator and return the resulting
    Unicode string."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, Py_ssize_t, Py_ssize_t, rffi.INT_real], rffi.INT_real, error=-1)
def PyUnicode_Tailmatch(space, str, substr, start, end, direction):
    """Return 1 if substr matches str*[*start:end] at the given tail end
    (direction == -1 means to do a prefix match, direction == 1 a suffix match),
    0 otherwise. Return -1 if an error occurred.
    
    This function used an int type for start and end. This
    might require changes in your code for properly supporting 64-bit
    systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, Py_ssize_t, Py_ssize_t, rffi.INT_real], Py_ssize_t, error=-2)
def PyUnicode_Find(space, str, substr, start, end, direction):
    """Return the first position of substr in str*[*start:end] using the given
    direction (direction == 1 means to do a forward search, direction == -1 a
    backward search).  The return value is the index of the first match; a value of
    -1 indicates that no match was found, and -2 indicates that an error
    occurred and an exception has been set.
    
    This function used an int type for start and end. This
    might require changes in your code for properly supporting 64-bit
    systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, Py_ssize_t, Py_ssize_t], Py_ssize_t, error=-1)
def PyUnicode_Count(space, str, substr, start, end):
    """Return the number of non-overlapping occurrences of substr in
    str[start:end].  Return -1 if an error occurred.
    
    This function returned an int type and used an int
    type for start and end. This might require changes in your code for
    properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject, Py_ssize_t], PyObject)
def PyUnicode_Replace(space, str, substr, replstr, maxcount):
    """Replace at most maxcount occurrences of substr in str with replstr and
    return the resulting Unicode object. maxcount == -1 means replace all
    occurrences.
    
    This function used an int type for maxcount. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.INT_real], PyObject)
def PyUnicode_RichCompare(space, left, right, op):
    """Rich compare two unicode strings and return one of the following:
    
    NULL in case an exception was raised
    
    Py_True or Py_False for successful comparisons
    
    Py_NotImplemented in case the type combination is unknown
    
    Note that Py_EQ and Py_NE comparisons can cause a
    UnicodeWarning in case the conversion of the arguments to Unicode fails
    with a UnicodeDecodeError.
    
    Possible values for op are Py_GT, Py_GE, Py_EQ,
    Py_NE, Py_LT, and Py_LE."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_Format(space, format, args):
    """Return a new string object from format and args; this is analogous to
    format % args.  The args argument must be a tuple."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyUnicode_Contains(space, container, element):
    """Check whether element is contained in container and return true or false
    accordingly.
    
    element has to coerce to a one element Unicode string. -1 is returned if
    there was an error."""
    raise NotImplementedError

@cpython_api([rffi.INT_real, rffi.CCHARPP], rffi.INT_real, error=2)
def Py_Main(space, argc, argv):
    """The main program for the standard interpreter.  This is made available for
    programs which embed Python.  The argc and argv parameters should be
    prepared exactly as those which are passed to a C program's main()
    function.  It is important to note that the argument list may be modified (but
    the contents of the strings pointed to by the argument list are not). The return
    value will be the integer passed to the sys.exit() function, 1 if the
    interpreter exits due to an exception, or 2 if the parameter list does not
    represent a valid Python command line.
    
    Note that if an otherwise unhandled SystemError is raised, this
    function will not return 1, but exit the process, as long as
    Py_InspectFlag is not set."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP], rffi.INT_real, error=-1)
def PyRun_AnyFile(space, fp, filename):
    """This is a simplified interface to PyRun_AnyFileExFlags() below, leaving
    closeit set to 0 and flags set to NULL."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, PyCompilerFlags], rffi.INT_real, error=-1)
def PyRun_AnyFileFlags(space, fp, filename, flags):
    """This is a simplified interface to PyRun_AnyFileExFlags() below, leaving
    the closeit argument set to 0."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, rffi.INT_real], rffi.INT_real, error=-1)
def PyRun_AnyFileEx(space, fp, filename, closeit):
    """This is a simplified interface to PyRun_AnyFileExFlags() below, leaving
    the flags argument set to NULL."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, rffi.INT_real, PyCompilerFlags], rffi.INT_real, error=-1)
def PyRun_AnyFileExFlags(space, fp, filename, closeit, flags):
    """If fp refers to a file associated with an interactive device (console or
    terminal input or Unix pseudo-terminal), return the value of
    PyRun_InteractiveLoop(), otherwise return the result of
    PyRun_SimpleFile().  If filename is NULL, this function uses
    "???" as the filename."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyCompilerFlags], rffi.INT_real, error=-1)
def PyRun_SimpleStringFlags(space, command, flags):
    """Executes the Python source code from command in the __main__ module
    according to the flags argument. If __main__ does not already exist, it
    is created.  Returns 0 on success or -1 if an exception was raised.  If
    there was an error, there is no way to get the exception information. For the
    meaning of flags, see below.
    
    Note that if an otherwise unhandled SystemError is raised, this
    function will not return -1, but exit the process, as long as
    Py_InspectFlag is not set."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP], rffi.INT_real, error=-1)
def PyRun_SimpleFile(space, fp, filename):
    """This is a simplified interface to PyRun_SimpleFileExFlags() below,
    leaving closeit set to 0 and flags set to NULL."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, PyCompilerFlags], rffi.INT_real, error=-1)
def PyRun_SimpleFileFlags(space, fp, filename, flags):
    """This is a simplified interface to PyRun_SimpleFileExFlags() below,
    leaving closeit set to 0."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, rffi.INT_real], rffi.INT_real, error=-1)
def PyRun_SimpleFileEx(space, fp, filename, closeit):
    """This is a simplified interface to PyRun_SimpleFileExFlags() below,
    leaving flags set to NULL."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, rffi.INT_real, PyCompilerFlags], rffi.INT_real, error=-1)
def PyRun_SimpleFileExFlags(space, fp, filename, closeit, flags):
    """Similar to PyRun_SimpleStringFlags(), but the Python source code is read
    from fp instead of an in-memory string. filename should be the name of the
    file.  If closeit is true, the file is closed before PyRun_SimpleFileExFlags
    returns."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP], rffi.INT_real, error=-1)
def PyRun_InteractiveOne(space, fp, filename):
    """This is a simplified interface to PyRun_InteractiveOneFlags() below,
    leaving flags set to NULL."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, PyCompilerFlags], rffi.INT_real, error=-1)
def PyRun_InteractiveOneFlags(space, fp, filename, flags):
    """Read and execute a single statement from a file associated with an
    interactive device according to the flags argument.  The user will be
    prompted using sys.ps1 and sys.ps2.  Returns 0 when the input was
    executed successfully, -1 if there was an exception, or an error code
    from the errcode.h include file distributed as part of Python if
    there was a parse error.  (Note that errcode.h is not included by
    Python.h, so must be included specifically if needed.)"""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP], rffi.INT_real, error=-1)
def PyRun_InteractiveLoop(space, fp, filename):
    """This is a simplified interface to PyRun_InteractiveLoopFlags() below,
    leaving flags set to NULL."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, PyCompilerFlags], rffi.INT_real, error=-1)
def PyRun_InteractiveLoopFlags(space, fp, filename, flags):
    """Read and execute statements from a file associated with an interactive device
    until EOF is reached.  The user will be prompted using sys.ps1 and
    sys.ps2.  Returns 0 at EOF."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.INT_real], _node)
def PyParser_SimpleParseString(space, str, start):
    """This is a simplified interface to
    PyParser_SimpleParseStringFlagsFilename() below, leaving  filename set
    to NULL and flags set to 0."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.INT_real, rffi.INT_real], _node)
def PyParser_SimpleParseStringFlags(space, str, start, flags):
    """This is a simplified interface to
    PyParser_SimpleParseStringFlagsFilename() below, leaving  filename set
    to NULL."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP, rffi.INT_real, rffi.INT_real], _node)
def PyParser_SimpleParseStringFlagsFilename(space, str, filename, start, flags):
    """Parse Python source code from str using the start token start according to
    the flags argument.  The result can be used to create a code object which can
    be evaluated efficiently. This is useful if a code fragment must be evaluated
    many times."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, rffi.INT_real], _node)
def PyParser_SimpleParseFile(space, fp, filename, start):
    """This is a simplified interface to PyParser_SimpleParseFileFlags() below,
    leaving flags set to 0"""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, rffi.INT_real, rffi.INT_real], _node)
def PyParser_SimpleParseFileFlags(space, fp, filename, start, flags):
    """Similar to PyParser_SimpleParseStringFlagsFilename(), but the Python
    source code is read from fp instead of an in-memory string."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.INT_real, PyObject, PyObject, PyCompilerFlags], PyObject)
def PyRun_StringFlags(space, str, start, globals, locals, flags):
    """Execute Python source code from str in the context specified by the
    dictionaries globals and locals with the compiler flags specified by
    flags.  The parameter start specifies the start token that should be used to
    parse the source code.
    
    Returns the result of executing the code as a Python object, or NULL if an
    exception was raised."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, rffi.INT_real, PyObject, PyObject, rffi.INT_real], PyObject)
def PyRun_FileEx(space, fp, filename, start, globals, locals, closeit):
    """This is a simplified interface to PyRun_FileExFlags() below, leaving
    flags set to NULL."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, rffi.INT_real, PyObject, PyObject, PyCompilerFlags], PyObject)
def PyRun_FileFlags(space, fp, filename, start, globals, locals, flags):
    """This is a simplified interface to PyRun_FileExFlags() below, leaving
    closeit set to 0."""
    raise NotImplementedError

@cpython_api([FILE, rffi.CCHARP, rffi.INT_real, PyObject, PyObject, rffi.INT_real, PyCompilerFlags], PyObject)
def PyRun_FileExFlags(space, fp, filename, start, globals, locals, closeit, flags):
    """Similar to PyRun_StringFlags(), but the Python source code is read from
    fp instead of an in-memory string. filename should be the name of the file.
    If closeit is true, the file is closed before PyRun_FileExFlags()
    returns."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP, rffi.INT_real], PyObject)
def Py_CompileString(space, str, filename, start):
    """This is a simplified interface to Py_CompileStringFlags() below, leaving
    flags set to NULL."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP, rffi.INT_real, PyCompilerFlags], PyObject)
def Py_CompileStringFlags(space, str, filename, start, flags):
    """Parse and compile the Python source code in str, returning the resulting code
    object.  The start token is given by start; this can be used to constrain the
    code which can be compiled and should be Py_eval_input,
    Py_file_input, or Py_single_input.  The filename specified by
    filename is used to construct the code object and may appear in tracebacks or
    SyntaxError exception messages.  This returns NULL if the code cannot
    be parsed or compiled."""
    raise NotImplementedError

@cpython_api([PyCodeObject, PyObject, PyObject], PyObject)
def PyEval_EvalCode(space, co, globals, locals):
    """This is a simplified interface to PyEval_EvalCodeEx(), with just
    the code object, and the dictionaries of global and local variables.
    The other arguments are set to NULL."""
    raise NotImplementedError

@cpython_api([PyCodeObject, PyObject, PyObject, PyObjectP, rffi.INT_real, PyObjectP, rffi.INT_real, PyObjectP, rffi.INT_real, PyObject], PyObject)
def PyEval_EvalCodeEx(space, co, globals, locals, args, argcount, kws, kwcount, defs, defcount, closure):
    """Evaluate a precompiled code object, given a particular environment for its
    evaluation.  This environment consists of dictionaries of global and local
    variables, arrays of arguments, keywords and defaults, and a closure tuple of
    cells."""
    raise NotImplementedError

@cpython_api([PyFrameObject], PyObject)
def PyEval_EvalFrame(space, f):
    """Evaluate an execution frame.  This is a simplified interface to
    PyEval_EvalFrameEx, for backward compatibility."""
    raise NotImplementedError

@cpython_api([PyFrameObject, rffi.INT_real], PyObject)
def PyEval_EvalFrameEx(space, f, throwflag):
    """This is the main, unvarnished function of Python interpretation.  It is
    literally 2000 lines long.  The code object associated with the execution
    frame f is executed, interpreting bytecode and executing calls as needed.
    The additional throwflag parameter can mostly be ignored - if true, then
    it causes an exception to immediately be thrown; this is used for the
    throw() methods of generator objects."""
    raise NotImplementedError

@cpython_api([PyCompilerFlags], rffi.INT_real, error=CANNOT_FAIL)
def PyEval_MergeCompilerFlags(space, cf):
    """This function changes the flags of the current evaluation frame, and returns
    true on success, false on failure."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyWeakref_Check(space, ob):
    """Return true if ob is either a reference or proxy object.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyWeakref_CheckRef(space, ob):
    """Return true if ob is a reference object.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyWeakref_CheckProxy(space, ob):
    """Return true if ob is a proxy object.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyWeakref_NewProxy(space, ob, callback):
    """Return a weak reference proxy object for the object ob.  This will always
    return a new reference, but is not guaranteed to create a new object; an
    existing proxy object may be returned.  The second parameter, callback, can
    be a callable object that receives notification when ob is garbage
    collected; it should accept a single parameter, which will be the weak
    reference object itself. callback may also be None or NULL.  If ob
    is not a weakly-referencable object, or if callback is not callable,
    None, or NULL, this will return NULL and raise TypeError.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyWeakref_GET_OBJECT(space, ref):
    """Similar to PyWeakref_GetObject(), but implemented as a macro that does no
    error checking.
    """
    borrow_from()
    raise NotImplementedError
