from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, generic_cpy_call, CANNOT_FAIL, Py_ssize_t, Py_ssize_tP,
    PyVarObject, Py_buffer,
    Py_TPFLAGS_HEAPTYPE, Py_LT, Py_LE, Py_EQ, Py_NE, Py_GT,
    Py_GE, CONST_STRING, FILEP, fwrite)
from pypy.module.cpyext.pyobject import (
    PyObject, PyObjectP, create_ref, from_ref, Py_IncRef, Py_DecRef,
    track_reference, get_typedescr, _Py_NewReference, RefcountState)
from pypy.module.cpyext.typeobject import PyTypeObjectPtr
from pypy.module.cpyext.pyerrors import PyErr_NoMemory, PyErr_BadInternalCall
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.interpreter.error import OperationError
import pypy.module.__builtin__.operation as operation


@cpython_api([Py_ssize_t], rffi.VOIDP)
def PyObject_MALLOC(space, size):
    return lltype.malloc(rffi.VOIDP.TO, size,
                         flavor='raw', zero=True)

@cpython_api([rffi.VOIDP], lltype.Void)
def PyObject_FREE(space, ptr):
    lltype.free(ptr, flavor='raw')

@cpython_api([PyTypeObjectPtr], PyObject)
def _PyObject_New(space, type):
    return _PyObject_NewVar(space, type, 0)

@cpython_api([PyTypeObjectPtr, Py_ssize_t], PyObject)
def _PyObject_NewVar(space, type, itemcount):
    w_type = from_ref(space, rffi.cast(PyObject, type))
    assert isinstance(w_type, W_TypeObject)
    typedescr = get_typedescr(w_type.instancetypedef)
    py_obj = typedescr.allocate(space, w_type, itemcount=itemcount)
    py_obj.c_ob_refcnt = 0
    if type.c_tp_itemsize == 0:
        w_obj = PyObject_Init(space, py_obj, type)
    else:
        py_objvar = rffi.cast(PyVarObject, py_obj)
        w_obj = PyObject_InitVar(space, py_objvar, type, itemcount)
    return py_obj

@cpython_api([rffi.VOIDP], lltype.Void)
def PyObject_Del(space, obj):
    lltype.free(obj, flavor='raw')

@cpython_api([PyObject], lltype.Void)
def PyObject_dealloc(space, obj):
    pto = obj.c_ob_type
    obj_voidp = rffi.cast(rffi.VOIDP, obj)
    generic_cpy_call(space, pto.c_tp_free, obj_voidp)
    if pto.c_tp_flags & Py_TPFLAGS_HEAPTYPE:
        Py_DecRef(space, rffi.cast(PyObject, pto))

@cpython_api([PyTypeObjectPtr], PyObject)
def _PyObject_GC_New(space, type):
    return _PyObject_New(space, type)

@cpython_api([rffi.VOIDP], lltype.Void)
def PyObject_GC_Del(space, obj):
    PyObject_Del(space, obj)

@cpython_api([rffi.VOIDP], lltype.Void)
def PyObject_GC_Track(space, op):
    """Adds the object op to the set of container objects tracked by the
    collector.  The collector can run at unexpected times so objects must be
    valid while being tracked.  This should be called once all the fields
    followed by the tp_traverse handler become valid, usually near the
    end of the constructor."""
    pass

@cpython_api([rffi.VOIDP], lltype.Void)
def PyObject_GC_UnTrack(space, op):
    """Remove the object op from the set of container objects tracked by the
    collector.  Note that PyObject_GC_Track() can be called again on
    this object to add it back to the set of tracked objects.  The deallocator
    (tp_dealloc handler) should call this for the object before any of
    the fields used by the tp_traverse handler become invalid."""
    pass

@cpython_api([PyObject], PyObjectP, error=CANNOT_FAIL)
def _PyObject_GetDictPtr(space, op):
    return lltype.nullptr(PyObjectP.TO)

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PyObject_IsTrue(space, w_obj):
    return space.is_true(w_obj)

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PyObject_Not(space, w_obj):
    return not space.is_true(w_obj)

@cpython_api([PyObject, PyObject], PyObject)
def PyObject_GetAttr(space, w_obj, w_name):
    """Retrieve an attribute named attr_name from object o. Returns the attribute
    value on success, or NULL on failure.  This is the equivalent of the Python
    expression o.attr_name."""
    return space.getattr(w_obj, w_name)

@cpython_api([PyObject, CONST_STRING], PyObject)
def PyObject_GetAttrString(space, w_obj, name_ptr):
    """Retrieve an attribute named attr_name from object o. Returns the attribute
    value on success, or NULL on failure. This is the equivalent of the Python
    expression o.attr_name."""
    name = rffi.charp2str(name_ptr)
    return space.getattr(w_obj, space.wrap(name))

@cpython_api([PyObject, PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyObject_HasAttr(space, w_obj, w_name):
    try:
        w_res = operation.hasattr(space, w_obj, w_name)
        return space.is_true(w_res)
    except OperationError:
        return 0

@cpython_api([PyObject, CONST_STRING], rffi.INT_real, error=CANNOT_FAIL)
def PyObject_HasAttrString(space, w_obj, name_ptr):
    try:
        name = rffi.charp2str(name_ptr)
        w_res = operation.hasattr(space, w_obj, space.wrap(name))
        return space.is_true(w_res)
    except OperationError:
        return 0

@cpython_api([PyObject, PyObject, PyObject], rffi.INT_real, error=-1)
def PyObject_SetAttr(space, w_obj, w_name, w_value):
    operation.setattr(space, w_obj, w_name, w_value)
    return 0

@cpython_api([PyObject, CONST_STRING, PyObject], rffi.INT_real, error=-1)
def PyObject_SetAttrString(space, w_obj, name_ptr, w_value):
    w_name = space.wrap(rffi.charp2str(name_ptr))
    operation.setattr(space, w_obj, w_name, w_value)
    return 0

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyObject_DelAttr(space, w_obj, w_name):
    """Delete attribute named attr_name, for object o. Returns -1 on failure.
    This is the equivalent of the Python statement del o.attr_name."""
    space.delattr(w_obj, w_name)
    return 0

@cpython_api([PyObject, CONST_STRING], rffi.INT_real, error=-1)
def PyObject_DelAttrString(space, w_obj, name_ptr):
    """Delete attribute named attr_name, for object o. Returns -1 on failure.
    This is the equivalent of the Python statement del o.attr_name."""
    w_name = space.wrap(rffi.charp2str(name_ptr))
    space.delattr(w_obj, w_name)
    return 0

@cpython_api([PyObject], lltype.Void)
def PyObject_ClearWeakRefs(space, w_object):
    w_object.clear_all_weakrefs()

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyObject_Size(space, w_obj):
    return space.len_w(w_obj)

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyCallable_Check(space, w_obj):
    """Determine if the object o is callable.  Return 1 if the object is callable
    and 0 otherwise.  This function always succeeds."""
    return int(space.is_true(space.callable(w_obj)))

@cpython_api([PyObject, PyObject], PyObject)
def PyObject_GetItem(space, w_obj, w_key):
    """Return element of o corresponding to the object key or NULL on failure.
    This is the equivalent of the Python expression o[key]."""
    return space.getitem(w_obj, w_key)

@cpython_api([PyObject, PyObject, PyObject], rffi.INT_real, error=-1)
def PyObject_SetItem(space, w_obj, w_key, w_value):
    """Map the object key to the value v.  Returns -1 on failure.  This is the
    equivalent of the Python statement o[key] = v."""
    space.setitem(w_obj, w_key, w_value)
    return 0

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyObject_DelItem(space, w_obj, w_key):
    """Delete the mapping for key from o.  Returns -1 on failure. This is the
    equivalent of the Python statement del o[key]."""
    space.delitem(w_obj, w_key)
    return 0

@cpython_api([PyObject, PyTypeObjectPtr], PyObject)
def PyObject_Init(space, obj, type):
    """Initialize a newly-allocated object op with its type and initial
    reference.  Returns the initialized object.  If type indicates that the
    object participates in the cyclic garbage detector, it is added to the
    detector's set of observed objects. Other fields of the object are not
    affected."""
    if not obj:
        PyErr_NoMemory(space)
    obj.c_ob_type = type
    _Py_NewReference(space, obj)
    return obj

@cpython_api([PyVarObject, PyTypeObjectPtr, Py_ssize_t], PyObject)
def PyObject_InitVar(space, py_obj, type, size):
    """This does everything PyObject_Init() does, and also initializes the
    length information for a variable-size object."""
    if not py_obj:
        PyErr_NoMemory(space)
    py_obj.c_ob_size = size
    return PyObject_Init(space, rffi.cast(PyObject, py_obj), type)

@cpython_api([PyObject], PyObject)
def PyObject_Type(space, w_obj):
    """When o is non-NULL, returns a type object corresponding to the object type
    of object o. On failure, raises SystemError and returns NULL.  This
    is equivalent to the Python expression type(o). This function increments the
    reference count of the return value. There's really no reason to use this
    function instead of the common expression o->ob_type, which returns a
    pointer of type PyTypeObject*, except when the incremented reference
    count is needed."""
    return space.type(w_obj)

@cpython_api([PyObject], PyObject)
def PyObject_Str(space, w_obj):
    return space.str(w_obj)

@cpython_api([PyObject], PyObject)
def PyObject_Repr(space, w_obj):
    """Compute a string representation of object o.  Returns the string
    representation on success, NULL on failure.  This is the equivalent of the
    Python expression repr(o).  Called by the repr() built-in function and
    by reverse quotes."""
    return space.repr(w_obj)

@cpython_api([PyObject], PyObject)
def PyObject_Unicode(space, w_obj):
    """Compute a Unicode string representation of object o.  Returns the Unicode
    string representation on success, NULL on failure. This is the equivalent of
    the Python expression unicode(o).  Called by the unicode() built-in
    function."""
    return space.call_function(space.w_unicode, w_obj)

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyObject_Compare(space, w_o1, w_o2):
    """
    Compare the values of o1 and o2 using a routine provided by o1, if one
    exists, otherwise with a routine provided by o2.  Returns the result of the
    comparison on success.  On error, the value returned is undefined; use
    PyErr_Occurred() to detect an error.  This is equivalent to the Python
    expression cmp(o1, o2)."""
    return space.int_w(space.cmp(w_o1, w_o2))

@cpython_api([PyObject, PyObject, rffi.INTP], rffi.INT_real, error=-1)
def PyObject_Cmp(space, w_o1, w_o2, result):
    """Compare the values of o1 and o2 using a routine provided by o1, if one
    exists, otherwise with a routine provided by o2.  The result of the
    comparison is returned in result.  Returns -1 on failure.  This is the
    equivalent of the Python statement result = cmp(o1, o2)."""
    res = space.int_w(space.cmp(w_o1, w_o2))
    result[0] = rffi.cast(rffi.INT, res)
    return 0

@cpython_api([PyObject, PyObject, rffi.INT_real], PyObject)
def PyObject_RichCompare(space, w_o1, w_o2, opid_int):
    """Compare the values of o1 and o2 using the operation specified by opid,
    which must be one of Py_LT, Py_LE, Py_EQ,
    Py_NE, Py_GT, or Py_GE, corresponding to <,
    <=, ==, !=, >, or >= respectively. This is the equivalent of
    the Python expression o1 op o2, where op is the operator corresponding
    to opid. Returns the value of the comparison on success, or NULL on failure."""
    opid = rffi.cast(lltype.Signed, opid_int)
    if opid == Py_LT: return space.lt(w_o1, w_o2)
    if opid == Py_LE: return space.le(w_o1, w_o2)
    if opid == Py_EQ: return space.eq(w_o1, w_o2)
    if opid == Py_NE: return space.ne(w_o1, w_o2)
    if opid == Py_GT: return space.gt(w_o1, w_o2)
    if opid == Py_GE: return space.ge(w_o1, w_o2)
    PyErr_BadInternalCall(space)

@cpython_api([PyObject, PyObject, rffi.INT_real], rffi.INT_real, error=-1)
def PyObject_RichCompareBool(space, ref1, ref2, opid):
    """Compare the values of o1 and o2 using the operation specified by opid,
    which must be one of Py_LT, Py_LE, Py_EQ,
    Py_NE, Py_GT, or Py_GE, corresponding to <,
    <=, ==, !=, >, or >= respectively. Returns -1 on error,
    0 if the result is false, 1 otherwise. This is the equivalent of the
    Python expression o1 op o2, where op is the operator corresponding to
    opid."""
    w_res = PyObject_RichCompare(space, ref1, ref2, opid)
    return int(space.is_true(w_res))

@cpython_api([PyObject], PyObject)
def PyObject_SelfIter(space, ref):
    """Undocumented function, this is wat CPython does."""
    Py_IncRef(space, ref)
    return ref

@cpython_api([PyObject, PyObject], PyObject)
def PyObject_GenericGetAttr(space, w_obj, w_name):
    """Generic attribute getter function that is meant to be put into a type
    object's tp_getattro slot.  It looks for a descriptor in the dictionary
    of classes in the object's MRO as well as an attribute in the object's
    __dict__ (if present).  As outlined in descriptors, data
    descriptors take preference over instance attributes, while non-data
    descriptors don't.  Otherwise, an AttributeError is raised."""
    from pypy.objspace.descroperation import object_getattribute
    w_descr = object_getattribute(space)
    return space.get_and_call_function(w_descr, w_obj, w_name)

@cpython_api([PyObject, PyObject, PyObject], rffi.INT_real, error=-1)
def PyObject_GenericSetAttr(space, w_obj, w_name, w_value):
    """Generic attribute setter function that is meant to be put into a type
    object's tp_setattro slot.  It looks for a data descriptor in the
    dictionary of classes in the object's MRO, and if found it takes preference
    over setting the attribute in the instance dictionary. Otherwise, the
    attribute is set in the object's __dict__ (if present).  Otherwise,
    an AttributeError is raised and -1 is returned."""
    from pypy.objspace.descroperation import object_setattr, object_delattr
    if w_value is not None:
        w_descr = object_setattr(space)
        space.get_and_call_function(w_descr, w_obj, w_name, w_value)
    else:
        w_descr = object_delattr(space)
        space.get_and_call_function(w_descr, w_obj, w_name)
    return 0

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyObject_IsInstance(space, w_inst, w_cls):
    """Returns 1 if inst is an instance of the class cls or a subclass of
    cls, or 0 if not.  On error, returns -1 and sets an exception.  If
    cls is a type object rather than a class object, PyObject_IsInstance()
    returns 1 if inst is of type cls.  If cls is a tuple, the check will
    be done against every entry in cls. The result will be 1 when at least one
    of the checks returns 1, otherwise it will be 0. If inst is not a class
    instance and cls is neither a type object, nor a class object, nor a
    tuple, inst must have a __class__ attribute --- the class relationship
    of the value of that attribute with cls will be used to determine the result
    of this function."""
    from pypy.module.__builtin__.abstractinst import abstract_isinstance_w
    return abstract_isinstance_w(space, w_inst, w_cls)

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyObject_IsSubclass(space, w_derived, w_cls):
    """Returns 1 if the class derived is identical to or derived from the class
    cls, otherwise returns 0.  In case of an error, returns -1. If cls
    is a tuple, the check will be done against every entry in cls. The result will
    be 1 when at least one of the checks returns 1, otherwise it will be
    0. If either derived or cls is not an actual class object (or tuple),
    this function uses the generic algorithm described above."""
    from pypy.module.__builtin__.abstractinst import abstract_issubclass_w
    return abstract_issubclass_w(space, w_derived, w_cls)

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PyObject_AsFileDescriptor(space, w_obj):
    """Derives a file descriptor from a Python object.  If the object is an
    integer or long integer, its value is returned.  If not, the object's
    fileno() method is called if it exists; the method must return an integer or
    long integer, which is returned as the file descriptor value.  Returns -1 on
    failure."""
    try:
        fd = space.int_w(w_obj)
    except OperationError:
        try:
            w_meth = space.getattr(w_obj, space.wrap('fileno'))
        except OperationError:
            raise OperationError(
                space.w_TypeError, space.wrap(
                "argument must be an int, or have a fileno() method."))
        else:
            w_fd = space.call_function(w_meth)
            fd = space.int_w(w_fd)

    if fd < 0:
        raise OperationError(
            space.w_ValueError, space.wrap(
            "file descriptor cannot be a negative integer"))

    return rffi.cast(rffi.INT_real, fd)


@cpython_api([PyObject], lltype.Signed, error=-1)
def PyObject_Hash(space, w_obj):
    """
    Compute and return the hash value of an object o.  On failure, return -1.
    This is the equivalent of the Python expression hash(o)."""
    return space.int_w(space.hash(w_obj))

@cpython_api([PyObject, rffi.CCHARPP, Py_ssize_tP], rffi.INT_real, error=-1)
def PyObject_AsCharBuffer(space, obj, bufferp, sizep):
    """Returns a pointer to a read-only memory location usable as
    character-based input.  The obj argument must support the single-segment
    character buffer interface.  On success, returns 0, sets buffer to the
    memory location and size to the buffer length.  Returns -1 and sets a
    TypeError on error.
    """
    pto = obj.c_ob_type

    pb = pto.c_tp_as_buffer
    if not (pb and pb.c_bf_getreadbuffer and pb.c_bf_getsegcount):
        raise OperationError(space.w_TypeError, space.wrap(
            "expected a character buffer object"))
    if generic_cpy_call(space, pb.c_bf_getsegcount,
                        obj, lltype.nullptr(Py_ssize_tP.TO)) != 1:
        raise OperationError(space.w_TypeError, space.wrap(
            "expected a single-segment buffer object"))
    size = generic_cpy_call(space, pb.c_bf_getcharbuffer,
                            obj, 0, bufferp)
    if size < 0:
        return -1
    sizep[0] = size
    return 0

# Also in include/object.h
Py_PRINT_RAW = 1 # No string quotes etc.

@cpython_api([PyObject, FILEP, rffi.INT_real], rffi.INT_real, error=-1)
def PyObject_Print(space, w_obj, fp, flags):
    """Print an object o, on file fp.  Returns -1 on error.  The flags argument
    is used to enable certain printing options.  The only option currently
    supported is Py_PRINT_RAW; if given, the str() of the object is written
    instead of the repr()."""
    if rffi.cast(lltype.Signed, flags) & Py_PRINT_RAW:
        w_str = space.str(w_obj)
    else:
        w_str = space.repr(w_obj)

    count = space.len_w(w_str)
    data = space.str_w(w_str)
    buf = rffi.get_nonmovingbuffer(data)
    try:
        fwrite(buf, 1, count, fp)
    finally:
        rffi.free_nonmovingbuffer(data, buf)
    return 0


@cpython_api([lltype.Ptr(Py_buffer), PyObject, rffi.VOIDP, Py_ssize_t,
              lltype.Signed, lltype.Signed], rffi.INT, error=CANNOT_FAIL)
def PyBuffer_FillInfo(space, view, obj, buf, length, readonly, flags):
    """
    Fills in a buffer-info structure correctly for an exporter that can only
    share a contiguous chunk of memory of "unsigned bytes" of the given
    length. Returns 0 on success and -1 (with raising an error) on error.

    This is not a complete re-implementation of the CPython API; it only
    provides a subset of CPython's behavior.
    """
    view.c_buf = buf
    view.c_len = length
    view.c_obj = obj
    Py_IncRef(space, obj)
    return 0


@cpython_api([lltype.Ptr(Py_buffer)], lltype.Void, error=CANNOT_FAIL)
def PyBuffer_Release(space, view):
    """
    Releases a Py_buffer obtained from getbuffer ParseTuple's s*.

    This is not a complete re-implementation of the CPython API; it only
    provides a subset of CPython's behavior.
    """
    Py_DecRef(space, view.c_obj)
