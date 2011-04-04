from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, cpython_struct, bootstrap_function, build_type_checkers,
    PyObjectFields, Py_ssize_t, CONST_STRING)
from pypy.module.cpyext.pyerrors import PyErr_BadArgument
from pypy.module.cpyext.pyobject import (
    PyObject, PyObjectP, Py_DecRef, make_ref, from_ref, track_reference,
    make_typedescr, get_typedescr)

##
## Implementation of PyStringObject
## ================================
##
## The problem
## -----------
##
## PyString_AsString() must return a (non-movable) pointer to the underlying
## buffer, whereas pypy strings are movable.  C code may temporarily store
## this address and use it, as long as it owns a reference to the PyObject.
## There is no "release" function to specify that the pointer is not needed
## any more.
##
## Also, the pointer may be used to fill the initial value of string. This is
## valid only when the string was just allocated, and is not used elsewhere.
##
## Solution
## --------
##
## PyStringObject contains two additional members: the size and a pointer to a
## char buffer; it may be NULL.
##
## - A string allocated by pypy will be converted into a PyStringObject with a
##   NULL buffer.  The first time PyString_AsString() is called, memory is
##   allocated (with flavor='raw') and content is copied.
##
## - A string allocated with PyString_FromStringAndSize(NULL, size) will
##   allocate a PyStringObject structure, and a buffer with the specified
##   size, but the reference won't be stored in the global map; there is no
##   corresponding object in pypy.  When from_ref() or Py_INCREF() is called,
##   the pypy string is created, and added to the global map of tracked
##   objects.  The buffer is then supposed to be immutable.
##
## - _PyString_Resize() works only on not-yet-pypy'd strings, and returns a
##   similar object.
##
## - PyString_Size() doesn't need to force the object.
##
## - There could be an (expensive!) check in from_ref() that the buffer still
##   corresponds to the pypy gc-managed string.
##

PyStringObjectStruct = lltype.ForwardReference()
PyStringObject = lltype.Ptr(PyStringObjectStruct)
PyStringObjectFields = PyObjectFields + \
    (("buffer", rffi.CCHARP), ("size", Py_ssize_t))
cpython_struct("PyStringObject", PyStringObjectFields, PyStringObjectStruct)

@bootstrap_function
def init_stringobject(space):
    "Type description of PyStringObject"
    make_typedescr(space.w_str.instancetypedef,
                   basestruct=PyStringObject.TO,
                   attach=string_attach,
                   dealloc=string_dealloc,
                   realize=string_realize)

PyString_Check, PyString_CheckExact = build_type_checkers("String", "w_str")

def new_empty_str(space, length):
    """
    Allocatse a PyStringObject and its buffer, but without a corresponding
    interpreter object.  The buffer may be mutated, until string_realize() is
    called.
    """
    typedescr = get_typedescr(space.w_str.instancetypedef)
    py_obj = typedescr.allocate(space, space.w_str)
    py_str = rffi.cast(PyStringObject, py_obj)

    buflen = length + 1
    py_str.c_size = length
    py_str.c_buffer = lltype.malloc(rffi.CCHARP.TO, buflen,
                                    flavor='raw', zero=True)
    return py_str

def string_attach(space, py_obj, w_obj):
    """
    Fills a newly allocated PyStringObject with the given string object. The
    buffer must not be modified.
    """
    py_str = rffi.cast(PyStringObject, py_obj)
    py_str.c_size = len(space.str_w(w_obj))
    py_str.c_buffer = lltype.nullptr(rffi.CCHARP.TO)

def string_realize(space, py_obj):
    """
    Creates the string in the interpreter. The PyStringObject buffer must not
    be modified after this call.
    """
    py_str = rffi.cast(PyStringObject, py_obj)
    s = rffi.charpsize2str(py_str.c_buffer, py_str.c_size)
    w_obj = space.wrap(s)
    track_reference(space, py_obj, w_obj)
    return w_obj

@cpython_api([PyObject], lltype.Void, external=False)
def string_dealloc(space, py_obj):
    """Frees allocated PyStringObject resources.
    """
    py_str = rffi.cast(PyStringObject, py_obj)
    if py_str.c_buffer:
        lltype.free(py_str.c_buffer, flavor="raw")
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, py_obj)

#_______________________________________________________________________

@cpython_api([CONST_STRING, Py_ssize_t], PyObject)
def PyString_FromStringAndSize(space, char_p, length):
    if char_p:
        s = rffi.charpsize2str(char_p, length)
        return make_ref(space, space.wrap(s))
    else:
        return rffi.cast(PyObject, new_empty_str(space, length))

@cpython_api([CONST_STRING], PyObject)
def PyString_FromString(space, char_p):
    s = rffi.charp2str(char_p)
    return space.wrap(s)

@cpython_api([PyObject], rffi.CCHARP, error=0)
def PyString_AsString(space, ref):
    ref_str = rffi.cast(PyStringObject, ref)
    if not ref_str.c_buffer:
        # copy string buffer
        w_str = from_ref(space, ref)
        s = space.str_w(w_str)
        ref_str.c_buffer = rffi.str2charp(s)
    return ref_str.c_buffer

@cpython_api([PyObject, rffi.CCHARPP, rffi.CArrayPtr(Py_ssize_t)], rffi.INT_real, error=-1)
def PyString_AsStringAndSize(space, ref, buffer, length):
    if not PyString_Check(space, ref):
        raise OperationError(space.w_TypeError, space.wrap(
            "PyString_AsStringAndSize only support strings"))
    ref_str = rffi.cast(PyStringObject, ref)
    if not ref_str.c_buffer:
        # copy string buffer
        w_str = from_ref(space, ref)
        s = space.str_w(w_str)
        ref_str.c_buffer = rffi.str2charp(s)
    buffer[0] = ref_str.c_buffer
    if length:
        length[0] = ref_str.c_size
    else:
        i = 0
        while ref_str.c_buffer[i] != '\0':
            i += 1
        if i != ref_str.c_size:
            raise OperationError(space.w_TypeError, space.wrap(
                "expected string without null bytes"))
    return 0

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyString_Size(space, ref):
    if from_ref(space, rffi.cast(PyObject, ref.c_ob_type)) is space.w_str:
        ref = rffi.cast(PyStringObject, ref)
        return ref.c_size
    else:
        w_obj = from_ref(space, ref)
        return space.len_w(w_obj)

@cpython_api([PyObjectP, Py_ssize_t], rffi.INT_real, error=-1)
def _PyString_Resize(space, ref, newsize):
    """A way to resize a string object even though it is "immutable". Only use this to
    build up a brand new string object; don't use this if the string may already be
    known in other parts of the code.  It is an error to call this function if the
    refcount on the input string object is not one. Pass the address of an existing
    string object as an lvalue (it may be written into), and the new size desired.
    On success, *string holds the resized string object and 0 is returned;
    the address in *string may differ from its input value.  If the reallocation
    fails, the original string object at *string is deallocated, *string is
    set to NULL, a memory exception is set, and -1 is returned.
    """
    # XXX always create a new string so far
    py_str = rffi.cast(PyStringObject, ref[0])
    if not py_str.c_buffer:
        raise OperationError(space.w_SystemError, space.wrap(
            "_PyString_Resize called on already created string"))
    try:
        py_newstr = new_empty_str(space, newsize)
    except MemoryError:
        Py_DecRef(space, ref[0])
        ref[0] = lltype.nullptr(PyObject.TO)
        raise
    to_cp = newsize
    oldsize = py_str.c_size
    if oldsize < newsize:
        to_cp = oldsize
    for i in range(to_cp):
        py_newstr.c_buffer[i] = py_str.c_buffer[i]
    Py_DecRef(space, ref[0])
    ref[0] = rffi.cast(PyObject, py_newstr)
    return 0

@cpython_api([PyObjectP, PyObject], lltype.Void)
def PyString_Concat(space, ref, w_newpart):
    """Create a new string object in *string containing the contents of newpart
    appended to string; the caller will own the new reference.  The reference to
    the old value of string will be stolen.  If the new string cannot be created,
    the old reference to string will still be discarded and the value of
    *string will be set to NULL; the appropriate exception will be set."""

    if not ref[0]:
        return

    if w_newpart is None or not PyString_Check(space, ref[0]) or \
            not PyString_Check(space, w_newpart):
         Py_DecRef(space, ref[0])
         ref[0] = lltype.nullptr(PyObject.TO)
         return
    w_str = from_ref(space, ref[0])
    w_newstr = space.add(w_str, w_newpart)
    Py_DecRef(space, ref[0])
    ref[0] = make_ref(space, w_newstr)

@cpython_api([PyObjectP, PyObject], lltype.Void)
def PyString_ConcatAndDel(space, ref, newpart):
    """Create a new string object in *string containing the contents of newpart
    appended to string.  This version decrements the reference count of newpart."""
    PyString_Concat(space, ref, newpart)
    Py_DecRef(space, newpart)

@cpython_api([PyObject, PyObject], PyObject)
def PyString_Format(space, w_format, w_args):
    """Return a new string object from format and args. Analogous to format %
    args.  The args argument must be a tuple."""
    return space.mod(w_format, w_args)

@cpython_api([CONST_STRING], PyObject)
def PyString_InternFromString(space, string):
    """A combination of PyString_FromString() and
    PyString_InternInPlace(), returning either a new string object that has
    been interned, or a new ("owned") reference to an earlier interned string
    object with the same value."""
    s = rffi.charp2str(string)
    return space.new_interned_str(s)

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyString_AsEncodedObject(space, w_str, encoding, errors):
    """Encode a string object using the codec registered for encoding and return
    the result as Python object. encoding and errors have the same meaning as
    the parameters of the same name in the string encode() method. The codec to
    be used is looked up using the Python codec registry. Return NULL if an
    exception was raised by the codec.

    This function is not available in 3.x and does not have a PyBytes alias."""
    if not PyString_Check(space, w_str):
        PyErr_BadArgument(space)

    w_encoding = w_errors = space.w_None
    if encoding:
        w_encoding = space.wrap(rffi.charp2str(encoding))
    if errors:
        w_errors = space.wrap(rffi.charp2str(errors))
    return space.call_method(w_str, 'encode', w_encoding, w_errors)
