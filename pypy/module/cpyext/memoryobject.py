from pypy.module.cpyext.api import (cpython_api, Py_buffer, CANNOT_FAIL,
                         Py_MAX_FMT, Py_MAX_NDIMS, build_type_checkers,
                         Py_ssize_tP, PyObjectFields, cpython_struct,
                         generic_cpy_call,
                         bootstrap_function, Py_bufferP)
from pypy.module.cpyext.pyobject import (PyObject, make_ref, as_pyobj, incref,
             decref, from_ref, make_typedescr)
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import widen
from pypy.interpreter.error import oefmt
from pypy.objspace.std.memoryobject import W_MemoryView
from pypy.module.cpyext.object import _dealloc
from pypy.module.cpyext.import_ import PyImport_Import
from pypy.module.cpyext.buffer import CBuffer

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
                   #realize=memory_realize,
                  )

def memory_attach(space, py_obj, w_obj, w_userdata=None):
    """
    Fills a newly allocated PyMemoryViewObject with the given W_MemoryView object.
    """
    py_obj = rffi.cast(PyMemoryViewObject, py_obj)
    py_obj.c_view.c_obj = rffi.cast(PyObject, 0)

def memory_realize(space, py_obj):
    """
    Creates the memory object in the interpreter
    """
    raise oefmt(space.w_NotImplementedError, "cannot call this yet")

@cpython_api([PyObject], lltype.Void, header=None)
def memory_dealloc(space, py_obj):
    mem_obj = rffi.cast(PyMemoryViewObject, py_obj)
    if mem_obj.c_view.c_obj:
        decref(space, mem_obj.c_view.c_obj)
    mem_obj.c_view.c_obj = rffi.cast(PyObject, 0)
    _dealloc(space, py_obj)

@cpython_api([PyObject, Py_bufferP, rffi.INT_real],
             rffi.INT_real, error=-1)
def PyObject_GetBuffer(space, exporter, view, flags):
    """Send a request to exporter to fill in view as specified by flags. If the
    exporter cannot provide a buffer of the exact type, it MUST raise
    PyExc_BufferError, set view->obj to NULL and return -1.

    On success, fill in view, set view->obj to a new reference to exporter and
    return 0. In the case of chained buffer providers that redirect requests
    to a single object, view->obj MAY refer to this object instead of exporter.

    Successful calls to PyObject_GetBuffer() must be paired with calls to
    PyBuffer_Release(), similar to malloc() and free(). Thus, after the
    consumer is done with the buffer, PyBuffer_Release() must be called exactly
    once.
    """
    # XXX compare this implementation with PyPy2's XXX
    pb = exporter.c_ob_type.c_tp_as_buffer
    if not pb or not pb.c_bf_getbuffer:
        w_exporter = from_ref(space, exporter)
        raise oefmt(space.w_TypeError,
            "a bytes-like object is required, not '%T'", w_exporter)
    return generic_cpy_call(space, pb.c_bf_getbuffer, exporter, view, flags)

@cpython_api([PyObject], Py_bufferP, error=CANNOT_FAIL)
def PyMemoryView_GET_BUFFER(space, w_obj):
    """Return a pointer to the buffer-info structure wrapped by the given
    object.  The object must be a memoryview instance; this macro doesn't
    check its type, you must do it yourself or you will risk crashes."""
    if not isinstance(w_obj, W_MemoryView):
        return lltype.nullptr(Py_buffer)
    py_memobj = rffi.cast(PyMemoryViewObject, as_pyobj(space, w_obj)) # no inc_ref
    view = py_memobj.c_view
    ndim = w_obj.buf.getndim()
    if ndim >= Py_MAX_NDIMS:
        # XXX warn?
        return view
    fill_Py_buffer(space, w_obj.buf, view)
    try:
        view.c_buf = rffi.cast(rffi.VOIDP, w_obj.buf.get_raw_address())
        #view.c_obj = make_ref(space, w_obj) # NO - this creates a ref cycle!
        rffi.setintfield(view, 'c_readonly', w_obj.buf.readonly)
    except ValueError:
        w_s = w_obj.descr_tobytes(space)
        view.c_obj = make_ref(space, w_s)
        view.c_buf = rffi.cast(rffi.VOIDP, rffi.str2charp(space.str_w(w_s), track_allocation=False))
        rffi.setintfield(view, 'c_readonly', 1)
    return view

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

@cpython_api([PyObject], PyObject)
def PyMemoryView_FromObject(space, w_obj):
    return space.call_method(space.builtin, "memoryview", w_obj)

@cpython_api([Py_bufferP], PyObject)
def PyMemoryView_FromBuffer(space, view):
    """Create a memoryview object wrapping the given buffer structure view.
    The memoryview object then owns the buffer represented by view, which
    means you shouldn't try to call PyBuffer_Release() yourself: it
    will be done on deallocation of the memoryview object."""
    w_obj = from_ref(space, view.c_obj)
    if isinstance(w_obj, W_MemoryView):
        return w_obj
    return space.call_method(space.builtin, "memoryview", w_obj)

@cpython_api([PyObject], PyObject)
def PyMemoryView_GET_BASE(space, w_obj):
    # return the obj field of the Py_buffer created by PyMemoryView_GET_BUFFER
    # XXX needed for numpy on py3k
    raise NotImplementedError('PyMemoryView_GET_BASE')

#XXX this function was removed in PyPy2, double-check that XXX
#@cpython_api([PyObject], lltype.Ptr(Py_buffer), error=CANNOT_FAIL)
#def PyMemoryView_GET_BUFFER(space, w_obj):
#    """Return a pointer to the buffer-info structure wrapped by the given
#    object.  The object must be a memoryview instance; this macro doesn't
#    check its type, you must do it yourself or you will risk crashes."""
#    view = lltype.malloc(Py_buffer, flavor='raw', zero=True)
#    if not isinstance(w_obj, W_MemoryView):
#        return view
#    ndim = w_obj.buf.getndim()
#    if ndim >= Py_MAX_NDIMS:
#        # XXX warn?
#        return view
#    fill_Py_buffer(space, w_obj.buf, view)
#    try:
#        view.c_buf = rffi.cast(rffi.VOIDP, w_obj.buf.get_raw_address())
#        view.c_obj = make_ref(space, w_obj)
#        rffi.setintfield(view, 'c_readonly', w_obj.buf.readonly)
#        isstr = False
#    except ValueError:
#        w_s = w_obj.descr_tobytes(space)
#        view.c_obj = make_ref(space, w_s)
#        view.c_buf = rffi.cast(rffi.VOIDP, rffi.str2charp(space.str_w(w_s), track_allocation=False))
#        rffi.setintfield(view, 'c_readonly', 1)
#        isstr = True
#    return view
