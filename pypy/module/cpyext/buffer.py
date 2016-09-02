from pypy.interpreter.error import oefmt
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, Py_buffer, Py_TPFLAGS_HAVE_NEWBUFFER, Py_ssize_tP)
from pypy.module.cpyext.pyobject import PyObject, as_pyobj, incref

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyObject_CheckBuffer(space, pyobj):
    """Return 1 if obj supports the buffer interface otherwise 0."""
    as_buffer = pyobj.c_ob_type.c_tp_as_buffer
    flags = pyobj.c_ob_type.c_tp_flags
    if (flags & Py_TPFLAGS_HAVE_NEWBUFFER and as_buffer.c_bf_getbuffer):
        return 1
    return 0  

@cpython_api([PyObject, lltype.Ptr(Py_buffer), rffi.INT_real],
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
    buf = space.call_method(w_obj, "__buffer__", space.newint(flags))
    try:
        view.c_buf = rffi.cast(rffi.VOIDP, buf.get_raw_address())
    except ValueError:
        raise BufferError("could not create buffer from object")
    view.c_len = buf.getlength()
    view.c_obj = as_pyobj(space, w_obj)
    incref(space, view.c_obj)
    ndim = buf.getndim()
    view.c_itemsize = buf.getitemsize()
    rffi.setintfield(view, 'c_readonly', int(buf.readonly))
    rffi.setintfield(view, 'c_ndim', ndim)
    view.c_format = rffi.str2charp(buf.getformat())
    view.c_shape = lltype.malloc(Py_ssize_tP.TO, ndim, flavor='raw')
    view.c_strides = lltype.malloc(Py_ssize_tP.TO, ndim, flavor='raw')
    shape = buf.getshape()
    strides = buf.getstrides()
    for i in range(ndim):
        view.c_shape[i] = shape[i]
        view.c_strides[i] = strides[i]
    view.c_suboffsets = lltype.nullptr(Py_ssize_tP.TO)
    view.c_internal = lltype.nullptr(rffi.VOIDP.TO)
    return 0

def _IsFortranContiguous(view):
    if view.ndim == 0:
        return 1
    if not view.strides:
        return view.ndim == 1
    sd = view.itemsize
    if view.ndim == 1:
        return view.shape[0] == 1 or sd == view.strides[0]
    for i in range(view.ndim):
        dim = view.shape[i]
        if dim == 0:
            return 1
        if view.strides[i] != sd:
            return 0
        sd *= dim
    return 1

def _IsCContiguous(view):
    if view.ndim == 0:
        return 1
    if not view.strides:
        return view.ndim == 1
    sd = view.itemsize
    if view.ndim == 1:
        return view.shape[0] == 1 or sd == view.strides[0]
    for i in range(view.ndim-1, -1, -1):
        dim = view.shape[i]
        if dim == 0:
            return 1
        if view.strides[i] != sd:
            return 0
        sd *= dim
    return 1
        

@cpython_api([lltype.Ptr(Py_buffer), lltype.Char], rffi.INT_real, error=CANNOT_FAIL)
def PyBuffer_IsContiguous(space, view, fort):
    """Return 1 if the memory defined by the view is C-style (fortran is
    'C') or Fortran-style (fortran is 'F') contiguous or either one
    (fortran is 'A').  Return 0 otherwise."""
    # traverse the strides, checking for consistent stride increases from
    # right-to-left (c) or left-to-right (fortran). Copied from cpython
    if not view.suboffsets:
        return 0
    if (fort == 'C'):
        return _IsCContiguous(view)
    elif (fort == 'F'):
        return _IsFortranContiguous(view)
    elif (fort == 'A'):
        return (_IsCContiguous(view) or _IsFortranContiguous(view))
    return 0

    
