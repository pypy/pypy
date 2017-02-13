from pypy.interpreter.error import oefmt
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, cpython_struct, bootstrap_function, build_type_checkers,
    PyVarObjectFields, Py_ssize_t, CONST_STRING, CANNOT_FAIL, slot_function)
from pypy.module.cpyext.pyerrors import PyErr_BadArgument
from pypy.module.cpyext.pyobject import (
    PyObject, PyObjectP, Py_DecRef, make_ref, from_ref, track_reference,
    make_typedescr, get_typedescr, as_pyobj, Py_IncRef, get_w_obj_and_decref,
    pyobj_has_w_obj)
from pypy.objspace.std.bytesobject import W_BytesObject

##
## Implementation of PyBytesObject
## ================================
##
## PyBytesObject has its own ob_sval buffer, so we have two copies of a string;
## one in the PyBytesObject returned from various C-API functions and another
## in the corresponding RPython object.
##
## The following calls can create a PyBytesObject without a correspoinding
## RPython object:
##
## PyBytes_FromStringAndSize(NULL, n) / PyString_FromStringAndSize(NULL, n)
##
## In the PyBytesObject returned, the ob_sval buffer may be modified as
## long as the freshly allocated PyBytesObject is not "forced" via a call
## to any of the more sophisticated C-API functions.
##
## Care has been taken in implementing the functions below, so that
## if they are called with a non-forced PyBytesObject, they will not
## unintentionally force the creation of a RPython object. As long as only these
## are used, the ob_sval buffer is still modifiable:
##
## PyBytes_AsString / PyString_AsString
## PyBytes_AS_STRING / PyString_AS_STRING
## PyBytes_AsStringAndSize / PyString_AsStringAndSize
## PyBytes_Size / PyString_Size
## PyBytes_Resize / PyString_Resize
## _PyBytes_Resize / _PyString_Resize (raises if called with a forced object)
##
## - There could be an (expensive!) check in from_ref() that the buffer still
##   corresponds to the pypy gc-managed string,
##

PyBytesObjectStruct = lltype.ForwardReference()
PyBytesObject = lltype.Ptr(PyBytesObjectStruct)
PyBytesObjectFields = PyVarObjectFields + \
    (("ob_shash", rffi.LONG), ("ob_sstate", rffi.INT), ("ob_sval", rffi.CArray(lltype.Char)))
cpython_struct("PyStringObject", PyBytesObjectFields, PyBytesObjectStruct)

@bootstrap_function
def init_bytesobject(space):
    "Type description of PyBytesObject"
    make_typedescr(space.w_bytes.layout.typedef,
                   basestruct=PyBytesObject.TO,
                   attach=bytes_attach,
                   dealloc=bytes_dealloc,
                   realize=bytes_realize)

PyString_Check, PyString_CheckExact = build_type_checkers("String", "w_bytes")

def new_empty_str(space, length):
    """
    Allocate a PyBytesObject and its ob_sval, but without a corresponding
    interpreter object.  The ob_sval may be mutated, until bytes_realize() is
    called.  Refcount of the result is 1.
    """
    typedescr = get_typedescr(space.w_bytes.layout.typedef)
    py_obj = typedescr.allocate(space, space.w_bytes, length)
    py_str = rffi.cast(PyBytesObject, py_obj)
    py_str.c_ob_shash = -1
    py_str.c_ob_sstate = rffi.cast(rffi.INT, 0) # SSTATE_NOT_INTERNED
    return py_str

def bytes_attach(space, py_obj, w_obj, w_userdata=None):
    """
    Copy RPython string object contents to a PyBytesObject. The
    c_ob_sval must not be modified.
    """
    py_str = rffi.cast(PyBytesObject, py_obj)
    s = space.bytes_w(w_obj)
    len_s = len(s)
    if py_str.c_ob_size  < len_s:
        raise oefmt(space.w_ValueError,
            "bytes_attach called on object with ob_size %d but trying to store %d",
            py_str.c_ob_size, len_s)
    with rffi.scoped_nonmovingbuffer(s) as s_ptr:
        rffi.c_memcpy(py_str.c_ob_sval, s_ptr, len_s)
    py_str.c_ob_sval[len_s] = '\0'
    # if py_obj has a tp_hash, this will try to call it, but the objects are
    # not fully linked yet
    #py_str.c_ob_shash = space.hash_w(w_obj)
    py_str.c_ob_shash = space.hash_w(space.newbytes(s))
    py_str.c_ob_sstate = rffi.cast(rffi.INT, 1) # SSTATE_INTERNED_MORTAL

def bytes_realize(space, py_obj):
    """
    Creates the string in the interpreter. The PyBytesObject ob_sval must not
    be modified after this call.
    """
    py_str = rffi.cast(PyBytesObject, py_obj)
    s = rffi.charpsize2str(py_str.c_ob_sval, py_str.c_ob_size)
    w_type = from_ref(space, rffi.cast(PyObject, py_obj.c_ob_type))
    w_obj = space.allocate_instance(W_BytesObject, w_type)
    w_obj.__init__(s)
    # if py_obj has a tp_hash, this will try to call it but the object is
    # not realized yet
    py_str.c_ob_shash = space.hash_w(space.newbytes(s))
    py_str.c_ob_sstate = rffi.cast(rffi.INT, 1) # SSTATE_INTERNED_MORTAL
    track_reference(space, py_obj, w_obj)
    return w_obj

@slot_function([PyObject], lltype.Void)
def bytes_dealloc(space, py_obj):
    """Frees allocated PyBytesObject resources.
    """
    from pypy.module.cpyext.object import _dealloc
    _dealloc(space, py_obj)

#_______________________________________________________________________

@cpython_api([CONST_STRING, Py_ssize_t], PyObject, result_is_ll=True)
def PyString_FromStringAndSize(space, char_p, length):
    if char_p:
        s = rffi.charpsize2str(char_p, length)
        return make_ref(space, space.newtext(s))
    else:
        return rffi.cast(PyObject, new_empty_str(space, length))

@cpython_api([CONST_STRING], PyObject)
def PyString_FromString(space, char_p):
    s = rffi.charp2str(char_p)
    return space.newtext(s)

@cpython_api([PyObject], rffi.CCHARP, error=0)
def PyString_AsString(space, ref):
    return _PyString_AsString(space, ref)

def _PyString_AsString(space, ref):
    if from_ref(space, rffi.cast(PyObject, ref.c_ob_type)) is space.w_bytes:
        pass    # typecheck returned "ok" without forcing 'ref' at all
    elif not PyString_Check(space, ref):   # otherwise, use the alternate way
        from pypy.module.cpyext.unicodeobject import (
            PyUnicode_Check, _PyUnicode_AsDefaultEncodedString)
        if PyUnicode_Check(space, ref):
            ref = _PyUnicode_AsDefaultEncodedString(space, ref, lltype.nullptr(rffi.CCHARP.TO))
        else:
            raise oefmt(space.w_TypeError,
                        "expected string or Unicode object, %T found",
                        from_ref(space, ref))
    ref_str = rffi.cast(PyBytesObject, ref)
    return ref_str.c_ob_sval

@cpython_api([rffi.VOIDP], rffi.CCHARP, error=0)
def PyString_AS_STRING(space, void_ref):
    ref = rffi.cast(PyObject, void_ref)
    # if no w_str is associated with this ref,
    # return the c-level ptr as RW
    if not pyobj_has_w_obj(ref):
        py_str = rffi.cast(PyBytesObject, ref)
        return py_str.c_ob_sval
    return _PyString_AsString(space, ref)

@cpython_api([PyObject, rffi.CCHARPP, rffi.CArrayPtr(Py_ssize_t)], rffi.INT_real, error=-1)
def PyString_AsStringAndSize(space, ref, data, length):
    if not PyString_Check(space, ref):
        from pypy.module.cpyext.unicodeobject import (
            PyUnicode_Check, _PyUnicode_AsDefaultEncodedString)
        if PyUnicode_Check(space, ref):
            ref = _PyUnicode_AsDefaultEncodedString(space, ref, lltype.nullptr(rffi.CCHARP.TO))
        else:
            raise oefmt(space.w_TypeError,
                        "expected string or Unicode object, %T found",
                        from_ref(space, ref))
    ref_str = rffi.cast(PyBytesObject, ref)
    data[0] = ref_str.c_ob_sval
    if length:
        length[0] = ref_str.c_ob_size
    else:
        i = 0
        while ref_str.c_ob_sval[i] != '\0':
            i += 1
        if i != ref_str.c_ob_size:
            raise oefmt(space.w_TypeError,
                        "expected string without null bytes")
    return 0

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyString_Size(space, ref):
    if from_ref(space, rffi.cast(PyObject, ref.c_ob_type)) is space.w_bytes:
        ref = rffi.cast(PyBytesObject, ref)
        return ref.c_ob_size
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
    if pyobj_has_w_obj(ref[0]):
        raise oefmt(space.w_SystemError,
                    "_PyString_Resize called on already created string")
    py_str = rffi.cast(PyBytesObject, ref[0])
    try:
        py_newstr = new_empty_str(space, newsize)
    except MemoryError:
        Py_DecRef(space, ref[0])
        ref[0] = lltype.nullptr(PyObject.TO)
        raise
    to_cp = newsize
    oldsize = py_str.c_ob_size
    if oldsize < newsize:
        to_cp = oldsize
    for i in range(to_cp):
        py_newstr.c_ob_sval[i] = py_str.c_ob_sval[i]
    Py_DecRef(space, ref[0])
    ref[0] = rffi.cast(PyObject, py_newstr)
    return 0

@cpython_api([PyObject, PyObject], rffi.INT, error=CANNOT_FAIL)
def _PyString_Eq(space, w_str1, w_str2):
    return space.eq_w(w_str1, w_str2)

@cpython_api([PyObjectP, PyObject], lltype.Void, error=None)
def PyString_Concat(space, ref, w_newpart):
    """Create a new string object in *string containing the contents of newpart
    appended to string; the caller will own the new reference.  The reference to
    the old value of string will be stolen.  If the new string cannot be created,
    the old reference to string will still be discarded and the value of
    *string will be set to NULL; the appropriate exception will be set."""

    old = ref[0]
    if not old:
        return

    ref[0] = lltype.nullptr(PyObject.TO)
    w_str = get_w_obj_and_decref(space, old)
    if w_newpart is not None and PyString_Check(space, old):
        # xxx if w_newpart is not a string or unicode or bytearray,
        # this might call __radd__() on it, whereas CPython raises
        # a TypeError in this case.
        w_newstr = space.add(w_str, w_newpart)
        ref[0] = make_ref(space, w_newstr)

@cpython_api([PyObjectP, PyObject], lltype.Void, error=None)
def PyString_ConcatAndDel(space, ref, newpart):
    """Create a new string object in *string containing the contents of newpart
    appended to string.  This version decrements the reference count of newpart."""
    try:
        PyString_Concat(space, ref, newpart)
    finally:
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

@cpython_api([PyObjectP], lltype.Void)
def PyString_InternInPlace(space, string):
    """Intern the argument *string in place.  The argument must be the
    address of a pointer variable pointing to a Python string object.
    If there is an existing interned string that is the same as
    *string, it sets *string to it (decrementing the reference count
    of the old string object and incrementing the reference count of
    the interned string object), otherwise it leaves *string alone and
    interns it (incrementing its reference count).  (Clarification:
    even though there is a lot of talk about reference counts, think
    of this function as reference-count-neutral; you own the object
    after the call if and only if you owned it before the call.)

    This function is not available in 3.x and does not have a PyBytes
    alias."""
    w_str = from_ref(space, string[0])
    w_str = space.new_interned_w_str(w_str)
    Py_DecRef(space, string[0])
    string[0] = make_ref(space, w_str)

@cpython_api([PyObject, CONST_STRING, CONST_STRING], PyObject)
def PyString_AsEncodedObject(space, w_str, encoding, errors):
    """Encode a string object using the codec registered for encoding and return
    the result as Python object. encoding and errors have the same meaning as
    the parameters of the same name in the string encode() method. The codec to
    be used is looked up using the Python codec registry. Return NULL if an
    exception was raised by the codec.

    This function is not available in 3.x and does not have a PyBytes alias."""
    if not PyString_Check(space, w_str):
        PyErr_BadArgument(space)

    w_encoding = w_errors = None
    if encoding:
        w_encoding = space.newtext(rffi.charp2str(encoding))
    if errors:
        w_errors = space.newtext(rffi.charp2str(errors))
    return space.call_method(w_str, 'encode', w_encoding, w_errors)

@cpython_api([PyObject, CONST_STRING, CONST_STRING], PyObject)
def PyString_AsDecodedObject(space, w_str, encoding, errors):
    """Decode a string object by passing it to the codec registered
    for encoding and return the result as Python object. encoding and
    errors have the same meaning as the parameters of the same name in
    the string encode() method.  The codec to be used is looked up
    using the Python codec registry. Return NULL if an exception was
    raised by the codec.

    This function is not available in 3.x and does not have a PyBytes alias."""
    if not PyString_Check(space, w_str):
        PyErr_BadArgument(space)

    w_encoding = w_errors = None
    if encoding:
        w_encoding = space.newtext(rffi.charp2str(encoding))
    if errors:
        w_errors = space.newtext(rffi.charp2str(errors))
    return space.call_method(w_str, "decode", w_encoding, w_errors)

@cpython_api([PyObject, PyObject], PyObject)
def _PyString_Join(space, w_sep, w_seq):
    return space.call_method(w_sep, 'join', w_seq)
