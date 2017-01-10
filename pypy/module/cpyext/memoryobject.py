from pypy.module.cpyext.api import (
    cpython_api, Py_buffer, CANNOT_FAIL, Py_MAX_FMT, Py_MAX_NDIMS,
    build_type_checkers, Py_ssize_tP, PyObjectFields, cpython_struct,
    bootstrap_function, Py_bufferP, slot_function)
from pypy.module.cpyext.pyobject import (
    PyObject, make_ref, as_pyobj, incref, decref, from_ref, make_typedescr,
    get_typedescr, track_reference)
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import widen
from pypy.objspace.std.memoryobject import W_MemoryView
from pypy.module.cpyext.object import _dealloc
from pypy.module.cpyext.import_ import PyImport_Import

PyMemoryView_Check, PyMemoryView_CheckExact = build_type_checkers("MemoryView")


PyMemoryViewObjectStruct = lltype.ForwardReference()
PyMemoryViewObject = lltype.Ptr(PyMemoryViewObjectStruct)
PyMemoryViewObjectFields = PyObjectFields + \
    (("view", Py_buffer),)
cpython_struct(
    "PyMemoryViewObject", PyMemoryViewObjectFields, PyMemoryViewObjectStruct,
    level=2)

@bootstrap_function
def init_memoryobject(space):
    "Type description of PyDictObject"
    make_typedescr(W_MemoryView.typedef,
                   basestruct=PyMemoryViewObject.TO,
                   attach=memory_attach,
                   dealloc=memory_dealloc,
                   realize=memory_realize,
                  )

def memory_attach(space, py_obj, w_obj, w_userdata=None):
    """
    Fills a newly allocated PyMemoryViewObject with the given W_MemoryView object.
    """
    assert isinstance(w_obj, W_MemoryView)
    py_obj = rffi.cast(PyMemoryViewObject, py_obj)
    view = py_obj.c_view
    ndim = w_obj.buf.getndim()
    if ndim >= Py_MAX_NDIMS:
        # XXX warn?
        return
    fill_Py_buffer(space, w_obj.buf, view)
    try:
        view.c_buf = rffi.cast(rffi.VOIDP, w_obj.buf.get_raw_address())
        view.c_obj = make_ref(space, w_userdata)
        rffi.setintfield(view, 'c_readonly', w_obj.buf.readonly)
    except ValueError:
        w_s = w_obj.descr_tobytes(space)
        view.c_obj = make_ref(space, w_s)
        view.c_buf = rffi.cast(rffi.VOIDP, rffi.str2charp(space.str_w(w_s),
                                             track_allocation=False))
        rffi.setintfield(view, 'c_readonly', 1)

def memory_realize(space, obj):
    """
    Creates the memory object in the interpreter
    """
    from pypy.module.cpyext.slotdefs import CPyBuffer, fq
    py_mem = rffi.cast(PyMemoryViewObject, obj)
    view = py_mem.c_view
    ndim = widen(view.c_ndim)
    shape = None
    if view.c_shape:
        shape = [view.c_shape[i] for i in range(ndim)]
    strides = None
    if view.c_strides:
        strides = [view.c_strides[i] for i in range(ndim)]
    format = 'B'
    if view.c_format:
        format = rffi.charp2str(view.c_format)
    buf = CPyBuffer(space, view.c_buf, view.c_len, from_ref(space, view.c_obj),
                    format=format, shape=shape, strides=strides,
                    ndim=ndim, itemsize=view.c_itemsize,
                    readonly=widen(view.c_readonly))
    # Ensure view.c_buf is released upon object finalization
    fq.register_finalizer(buf)
    # Allow subclassing W_MemeoryView
    w_type = from_ref(space, rffi.cast(PyObject, obj.c_ob_type))
    w_obj = space.allocate_instance(W_MemoryView, w_type)
    w_obj.__init__(buf)
    track_reference(space, obj, w_obj)
    return w_obj

@slot_function([PyObject], lltype.Void)
def memory_dealloc(space, py_obj):
    mem_obj = rffi.cast(PyMemoryViewObject, py_obj)
    if mem_obj.c_view.c_obj:
        decref(space, mem_obj.c_view.c_obj)
    mem_obj.c_view.c_obj = rffi.cast(PyObject, 0)
    _dealloc(space, py_obj)


@cpython_api([PyObject, Py_bufferP, rffi.INT_real],
             rffi.INT_real, error=-1)
def PyObject_GetBuffer(space, w_obj, view, flags):
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

    0 is returned on success and -1 on error."""
    flags = widen(flags)
    buf = space.buffer_w(w_obj, flags)
    try:
        view.c_buf = rffi.cast(rffi.VOIDP, buf.get_raw_address())
    except ValueError:
        if not space.isinstance_w(w_obj, space.w_str):
            # XXX Python 3?
            raise BufferError("could not create buffer from object")
        view.c_buf = rffi.cast(rffi.VOIDP, rffi.str2charp(space.str_w(w_obj), track_allocation=False))
        rffi.setintfield(view, 'c_readonly', 1)
    ret = fill_Py_buffer(space, buf, view)
    view.c_obj = make_ref(space, w_obj)
    return ret

@cpython_api([PyObject], Py_bufferP, error=CANNOT_FAIL)
def PyMemoryView_GET_BUFFER(space, pyobj):
    """Return a pointer to the buffer-info structure wrapped by the given
    object.  The object must be a memoryview instance; this macro doesn't
    check its type, you must do it yourself or you will risk crashes."""
    # XXX move to a c-macro
    py_memobj = rffi.cast(PyMemoryViewObject, pyobj)
    return py_memobj.c_view

def fill_Py_buffer(space, buf, view):
    # c_buf, c_obj have been filled in
    ndim = buf.getndim()
    view.c_len = buf.getlength()
    view.c_itemsize = buf.getitemsize()
    rffi.setintfield(view, 'c_ndim', ndim)
    view.c_format = rffi.cast(rffi.CCHARP, view.c__format)
    fmt = buf.getformat()
    n = Py_MAX_FMT - 1 # NULL terminated buffer
    if len(fmt) > n:
        w_message = space.newbytes("PyPy specific Py_MAX_FMT is %d which is too "
                           "small for buffer format, %d needed" % (
                           Py_MAX_FMT, len(fmt)))
        w_stacklevel = space.newint(1)
        w_module = PyImport_Import(space, space.newbytes("warnings"))
        w_warn = space.getattr(w_module, space.newbytes("warn"))
        space.call_function(w_warn, w_message, space.w_None, w_stacklevel)
    else:
        n = len(fmt)
    for i in range(n):
        view.c_format[i] = fmt[i]
    view.c_format[n] = '\x00'
    if ndim > 0:
        view.c_shape = rffi.cast(Py_ssize_tP, view.c__shape)
        view.c_strides = rffi.cast(Py_ssize_tP, view.c__strides)
        shape = buf.getshape()
        strides = buf.getstrides()
        for i in range(ndim):
            view.c_shape[i] = shape[i]
            view.c_strides[i] = strides[i]
    else:
        view.c_shape = lltype.nullptr(Py_ssize_tP.TO)
        view.c_strides = lltype.nullptr(Py_ssize_tP.TO)
    view.c_suboffsets = lltype.nullptr(Py_ssize_tP.TO)
    view.c_internal = lltype.nullptr(rffi.VOIDP.TO)
    return 0

def _IsFortranContiguous(view):
    ndim = widen(view.c_ndim)
    if ndim == 0:
        return 1
    if not view.c_strides:
        return ndim == 1
    sd = view.c_itemsize
    if ndim == 1:
        return view.c_shape[0] == 1 or sd == view.c_strides[0]
    for i in range(view.c_ndim):
        dim = view.c_shape[i]
        if dim == 0:
            return 1
        if view.c_strides[i] != sd:
            return 0
        sd *= dim
    return 1

def _IsCContiguous(view):
    ndim = widen(view.c_ndim)
    if ndim == 0:
        return 1
    if not view.c_strides:
        return ndim == 1
    sd = view.c_itemsize
    if ndim == 1:
        return view.c_shape[0] == 1 or sd == view.c_strides[0]
    for i in range(ndim - 1, -1, -1):
        dim = view.c_shape[i]
        if dim == 0:
            return 1
        if view.c_strides[i] != sd:
            return 0
        sd *= dim
    return 1

@cpython_api([Py_bufferP, lltype.Char], rffi.INT_real, error=CANNOT_FAIL)
def PyBuffer_IsContiguous(space, view, fort):
    """Return 1 if the memory defined by the view is C-style (fort is
    'C') or Fortran-style (fort is 'F') contiguous or either one
    (fort is 'A').  Return 0 otherwise."""
    # traverse the strides, checking for consistent stride increases from
    # right-to-left (c) or left-to-right (fortran). Copied from cpython
    if view.c_suboffsets:
        return 0
    if (fort == 'C'):
        return _IsCContiguous(view)
    elif (fort == 'F'):
        return _IsFortranContiguous(view)
    elif (fort == 'A'):
        return (_IsCContiguous(view) or _IsFortranContiguous(view))
    return 0

@cpython_api([PyObject], PyObject, result_is_ll=True)
def PyMemoryView_FromObject(space, w_obj):
    w_memview = space.call_method(space.builtin, "memoryview", w_obj)
    py_memview = make_ref(space, w_memview, w_obj)
    return py_memview

@cpython_api([Py_bufferP], PyObject, result_is_ll=True)
def PyMemoryView_FromBuffer(space, view):
    """Create a memoryview object wrapping the given buffer-info structure view.
    The memoryview object then owns the buffer, which means you shouldn't
    try to release it yourself: it will be released on deallocation of the
    memoryview object."""
    # XXX this should allocate a PyMemoryViewObject and
    # copy view into obj.c_view, without creating a new view.c_obj
    typedescr = get_typedescr(W_MemoryView.typedef)
    py_obj = typedescr.allocate(space, space.w_memoryview)
    py_mem = rffi.cast(PyMemoryViewObject, py_obj)
    mview = py_mem.c_view
    mview.c_buf = view.c_buf
    mview.c_obj = view.c_obj
    mview.c_len = view.c_len
    mview.c_itemsize = view.c_itemsize
    mview.c_readonly = view.c_readonly
    mview.c_ndim = view.c_ndim
    mview.c_format = view.c_format
    if view.c_strides == rffi.cast(Py_ssize_tP, view.c__strides):
        py_mem.c_view.c_strides = rffi.cast(Py_ssize_tP, py_mem.c_view.c__strides)
        for i in range(view.c_ndim):
            py_mem.c_view.c_strides[i] = view.c_strides[i]
    else:
        # some externally allocated memory chunk
        py_mem.c_view.c_strides = view.c_strides
    if view.c_shape == rffi.cast(Py_ssize_tP, view.c__shape):
        py_mem.c_view.c_shape = rffi.cast(Py_ssize_tP, py_mem.c_view.c__shape)
        for i in range(view.c_ndim):
            py_mem.c_view.c_shape[i] = view.c_shape[i]
    else:
        # some externally allocated memory chunk
        py_mem.c_view.c_shape = view.c_shape
    # XXX ignore suboffsets?
    return py_obj

@cpython_api([PyObject], PyObject)
def PyMemoryView_GET_BASE(space, w_obj):
    # return the obj field of the Py_buffer created by PyMemoryView_GET_BUFFER
    # XXX needed for numpy on py3k
    raise NotImplementedError('PyMemoryView_GET_BASE')

