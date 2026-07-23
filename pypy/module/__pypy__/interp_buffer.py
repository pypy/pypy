"""
Allow use of the buffer interface from python
"""

from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.objspace.std.memoryobject import BufferViewND
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.py_buffer import W_BufferExporter
from pypy.interpreter.typedef import TypeDef, generic_new_descr
from pypy.interpreter.typedef import make_weakref_descr

class W_Bufferable(W_Root):
    def __init__(self, space):
        pass

    def descr_buffer(self, space, w_flags):
        if type(self) is W_Bufferable:
            raise oefmt(space.w_ValueError, "override __buffer__ in a subclass")
        return space.call_method(self, '__buffer__', w_flags)

    def readbuf_w(self, space):
        mv = space.call_method(self, '__buffer__', space.newint(0))
        buf = mv.buffer_w(space, 0)
        with buf:
            result = buf.as_readbuf()
        return result

W_Bufferable.typedef = TypeDef("Bufferable", None, None, 'read-write',
    __doc__ = """a helper class for a app-level class (like _ctypes.Array)
that want to support tp_as_buffer.bf_getbuffer via a __buffer__ method""",
    __new__ = generic_new_descr(W_Bufferable),
    __buffer__ = interp2app(W_Bufferable.descr_buffer),
)

@unwrap_spec(itemsize=int, format='text')
def newmemoryview(space, w_obj, itemsize, format, w_shape=None, w_strides=None):
    '''
    newmemoryview(buf, itemsize, format, shape=None, strides=None)
    '''
    if not space.isinstance_w(w_obj, space.w_memoryview):
        raise oefmt(space.w_ValueError, "memoryview expected")
    # minimal error checking
    lgt = space.len_w(w_obj)
    old_size = w_obj.getitemsize()
    nbytes = lgt * old_size
    strides = []
    shape = []
    if w_strides:
        for w_v in space.listview(w_strides):
            v = space.int_w(w_v)
            strides.append(v)
        if not w_shape and len(strides) != 1:
            raise oefmt(space.w_ValueError,
                  "strides must have a single value if shape not provided")
    if w_shape and w_strides:
        shape_w = space.listview(w_shape)
        if len(shape_w) != len(strides):
            raise oefmt(space.w_ValueError,
                  "shape %s does not match strides %s",
                  str(shape), str(strides))
        for w_v in space.listview(w_shape):
            v = space.int_w(w_v)
            shape.append(v)
        tot = 1 
        for i in range(len(strides) - 1, -1, -1):
            if strides[i] % tot != 0:
                raise oefmt(space.w_ValueError,
                            "strides does not match shape, itemsize")
            tot *= shape[i] * (strides[i] / tot)
        if tot != nbytes:
            raise oefmt(space.w_ValueError,
                  "shape * strides / itemsize %s * %s / %d does not match obj data %d * %d",
                  str(shape), str(strides), itemsize, lgt, old_size)
    elif w_shape:
        tot = 1
        for w_v in space.listview(w_shape):
            v = space.int_w(w_v)
            shape.append(v)
            tot *= v
        if tot * itemsize != nbytes:
            raise oefmt(space.w_ValueError,
                  "shape/itemsize %s/%d does not match obj len/itemsize %d/%d",
                  str(shape), itemsize, lgt, old_size)
    else:
        if itemsize == 0:
            raise oefmt(space.w_ValueError,
                "cannot guess shape when itemsize==0")
        if nbytes % itemsize != 0:
            raise oefmt(space.w_ValueError,
                  "itemsize %d does not match obj len/itemsize %d/%d",
                  itemsize, lgt, old_size)
        shape = [nbytes / itemsize,]
    ndim = len(shape)
    if not w_strides:
        # start from the right, c-order layout
        strides = [itemsize] * ndim
        for v in range(ndim - 2, -1, -1):
            strides[v] = strides[v + 1] * shape[v + 1]
    if len(strides) != ndim:
        raise oefmt(space.w_ValueError,
              "shape %s does not match strides %s",
              str(shape), str(strides))
    # check that the strides are not too big
    if nbytes > 0:
        for i in range(ndim):
            if strides[i] * shape[i] > nbytes:
                raise oefmt(space.w_ValueError,
                      "shape %s and strides %s exceed object size %d",
                      shape, strides, nbytes)
    view = space.buffer_w(w_obj, 0)
    # w_obj (the input memoryview) is a borrowed view: it owns and releases the
    # underlying export itself.  Pass it as the owning object so it is kept
    # alive as long as the returned memoryview lives.
    return space.newmemoryview(FormatBufferViewND(view, itemsize, format, ndim,
                                                  shape, strides, w_obj=w_obj))

class FormatBufferViewND(BufferViewND):
    _immutable_ = True
    _attrs_ = ['readonly', 'parent', 'ndim', 'shape', 'strides',
               'format', 'itemsize']
    def __init__(self, parent, itemsize, format, ndim, shape, strides, w_obj=None):
        BufferViewND.__init__(self, parent, ndim, shape, strides, w_obj=w_obj)
        self.format = format
        self.itemsize = itemsize

    def getformat(self):
        return self.format

    def getitemsize(self):
        return self.itemsize

class W_PickleBuffer(W_BufferExporter):
    """ Wrapper for potentially out-of-band buffers """
    def __init__(self, space, w_obj):
        # Remember the object we were constructed from: re-acquiring from it
        # (rather than from self.buf.w_obj, which points at the root exporter)
        # preserves a sliced/strided source's shape and strides.
        self.w_source = w_obj
        self.buf = space.buffer_w(w_obj, space.BUF_FULL_RO)
        if self.buf is not None and self.buf.needs_release():
            self.register_finalizer(space)

    def check(self, space):
        if self.buf is None:
            raise oefmt(space.w_ValueError, 'operation forbidden on released PickleBuffer object')

    def _release_buf(self):
        buf = self.buf
        if buf is not None:
            self.buf = None
            buf.releasebuffer()

    def _finalize_(self):
        self._release_buf()

    def descr_raw(self, space):
        """
        Return a memoryview of the raw memory underlying this buffer.
        Will raise BufferError is the buffer isn't contiguous.
        """
        self.check(space)
        w_obj = self.w_source
        if w_obj is not None and w_obj is not self:
            view = space.buffer_w(w_obj, space.BUF_FULL_RO)
        else:
            view = self.buf
        # Own the export only when buffer_w acquired a fresh one; when w_obj
        # already owns it (a memoryview source yields a borrowed
        # NonOwningReleaseView, needs_release() == False) this memoryview just
        # borrows.
        return view.wrap(space, owns_export=view.needs_release())

    def descr_release(self, space):
        """
        Release the underlying buffer exposed by the PickleBuffer object.
        """
        self._release_buf()

    def buffer_w(self, space, flags):
        self.check(space)
        space.check_buf_flags(flags, self.buf.readonly)
        w_obj = self.w_source
        if w_obj is not None and w_obj is not self:
            return space.buffer_w(w_obj, flags)
        return self.buf

    def bf_getbuffer(self, space, view, flags):
        self.check(space)
        # Forward to the underlying exporter (see buffer_w comment).
        w_obj = self.w_source
        if w_obj is not None and w_obj is not self:
            w_obj.bf_getbuffer(space, view, flags)
            return
        space.check_buf_flags(flags, self.buf.readonly)
        v = self.buf
        view.obj = self
        view.buf = v.as_readbuf() if v.readonly else v.as_writebuf()
        view.length = v.getlength()
        view.readonly = v.readonly
        view.itemsize = v.getitemsize()
        view.ndim = v.getndim()
        view.format = v.getformat()
        view.shape = v.getshape()
        view.strides = v.getstrides()


def descr_new_picklebuffer(space, w_type, w_obj):
    return W_PickleBuffer(space, w_obj)

W_PickleBuffer.typedef = TypeDef("PickleBuffer", None, None, 'read',
    __new__ = interp2app(descr_new_picklebuffer),
    raw = interp2app(W_PickleBuffer.descr_raw),
    release = interp2app(W_PickleBuffer.descr_release),
    __weakref__=make_weakref_descr(W_PickleBuffer),
)
W_PickleBuffer.typedef.acceptable_as_base_class = False
