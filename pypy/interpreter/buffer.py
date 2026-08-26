from rpython.rlib.rstruct.error import StructError
from rpython.rlib.buffer import StringBuffer, SubBuffer, RawBuffer
from rpython.rlib.mutbuffer import MutableStringBuffer

from pypy.interpreter.error import oefmt, OperationError

class BufferInterfaceNotFound(Exception):
    pass



class BufferView(object):
    """Abstract base class for buffers."""
    _attrs_ = ['readonly', 'w_obj']
    _immutable_ = True

    def getlength(self):
        """Returns the size in bytes (even if getitemsize() > 1)."""
        raise NotImplementedError

    def as_str(self):
        "Returns an interp-level string with the whole content of the buffer."
        from rpython.rlib.rstring import StringBuilder
        if self.getndim() == 0:
            itemsize = self.getitemsize()
            return self.getbytes(0, itemsize)
        nchunks = self.getlength()
        data = StringBuilder(nchunks)
        self._copy_rec(0, data, 0)
        return data.build()

    def getbytes(self, start, size):
        """Return `size` bytes starting at byte offset `start`.

        This is a low-level operation, it is up to the caller to ensure that
        the data requested actually correspond to items accessible from the
        BufferView.
        Note that `start` may be negative, e.g. if the buffer is reversed.
        """
        raise NotImplementedError

    def setbytes(self, start, string):
        raise NotImplementedError

    def get_raw_address(self):
        raise ValueError("no raw buffer")

    def as_readbuf(self):
        # Inefficient. May be overridden.
        return StringBuffer(self.as_str())

    def as_writebuf(self):
        """Return a writable Buffer sharing the same data as `self`."""
        raise BufferInterfaceNotFound

    def getformat(self):
        raise NotImplementedError

    def getitemsize(self):
        raise NotImplementedError

    def getndim(self):
        raise NotImplementedError

    def getshape(self):
        raise NotImplementedError

    def getstrides(self):
        raise NotImplementedError

    def releasebuffer(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exctype, excvalue, exctb):
        self.releasebuffer()
        return False

    def needs_release(self):
        return False

    def value_from_bytes(self, space, s):
        from pypy.module.struct.formatiterator import UnpackFormatIterator
        buf = StringBuffer(s)
        fmtiter = UnpackFormatIterator(space, buf)
        fmtiter.interpret(self.getformat())
        return fmtiter.result_w[0]

    def bytes_from_value(self, space, w_val):
        from pypy.module.struct.formatiterator import PackFormatIterator
        itemsize = self.getitemsize()
        buf = MutableStringBuffer(itemsize)
        fmtiter = PackFormatIterator(space, buf, [w_val])
        try:
            fmtiter.interpret(self.getformat())
        except StructError as e:
            raise oefmt(space.w_TypeError,
                        "memoryview: invalid type for format '%s'",
                        self.getformat())
        return buf.finish()

    def _copy_rec(self, idim, data, off):
        shapes = self.getshape()
        shape = shapes[idim]
        strides = self.getstrides()

        if self.getndim() - 1 == idim:
            self._copy_base(data, off)
            return

        for i in range(shape):
            self._copy_rec(idim + 1, data, off)
            off += strides[idim]

    def _copy_base(self, data, off):
        shapes = self.getshape()
        step = shapes[-1]
        strides = self.getstrides()
        stride = strides[-1]
        if not stride:
            return
        itemsize = self.getitemsize()
        for i in range(off, off + stride * step, stride):
            bytes = self.getbytes(i, itemsize)
            data.append(bytes)

    def get_offset(self, space, dim, index):
        "Convert index at dimension `dim` into a byte offset"
        shape = self.getshape()
        nitems = shape[dim]
        if index < 0:
            index += nitems
        if index < 0 or index >= nitems:
            raise oefmt(space.w_IndexError,
                "index out of bounds on dimension %d", dim + 1)
        # TODO suboffsets?
        strides = self.getstrides()
        return strides[dim] * index

    def w_getitem(self, space, idx):
        offset = self.get_offset(space, 0, idx)
        itemsize = self.getitemsize()
        # TODO: this probably isn't very fast
        data = self.getbytes(offset, itemsize)
        return self.value_from_bytes(space, data)

    def new_slice(self, start, step, slicelength):
        return BufferSlice(self, start, step, slicelength, w_obj=self.w_obj)

    def setitem_w(self, space, idx, w_obj):
        offset = self.get_offset(space, 0, idx)
        # TODO: this probably isn't very fast
        byteval = self.bytes_from_value(space, w_obj)
        self.setbytes(offset, byteval)

    def w_tolist(self, space):
        dim = self.getndim()
        if dim == 0:
            raise NotImplementedError
        elif dim == 1:
            n = self.getshape()[0]
            values_w = [self.w_getitem(space, i) for i in range(n)]
            return space.newlist(values_w)
        else:
            return self._tolist_rec(space, 0, 0)

    def _tolist_rec(self, space, start, idim):
        strides = self.getstrides()
        shape = self.getshape()
        #
        dim = idim + 1
        stride = strides[idim]
        itemsize = self.getitemsize()
        dimshape = shape[idim]
        #
        if dim >= self.getndim():
            bytecount = (stride * dimshape)
            values_w = [
                self.value_from_bytes(space, self.getbytes(pos, itemsize))
                for pos in range(start, start + bytecount, stride)]
            return space.newlist(values_w)

        items = [None] * dimshape
        for i in range(dimshape):
            item = self._tolist_rec(space, start, idim + 1)
            items[i] = item
            start += stride

        return space.newlist(items)

    def wrap(self, space, owns_export=True):
        return space.newmemoryview(self, owns_export=owns_export)


class RawBufferView_Base(BufferView):
    """Abstract base class for views into RawBuffers"""
    _attrs_ = ['readonly', 'data']
    _immutable_ = True

    def getlength(self):
        return self.data.getlength()

    def as_str(self):
        return self.data.as_str()

    def getbytes(self, start, size):
        return self.data[start:start + size]

    def setbytes(self, offset, s):
        return self.data.setslice(offset, s)

    def get_raw_address(self):
        return self.data.get_raw_address()

    def as_readbuf(self):
        return self.data

    def as_writebuf(self):
        assert not self.data.readonly
        return self.data

    def releasebuffer(self):
        self.data.releasebuffer()

    def needs_release(self):
        return self.data.needs_release()


class RawBufferView(RawBufferView_Base):
    _attrs_ = ['readonly', 'data', 'fmt', 'itemsize']
    _immutable_ = True

    def __init__(self, data, fmt, itemsize, w_obj=None):
        assert isinstance(data, RawBuffer)
        self.data = data
        self.readonly = data.readonly
        self.fmt = fmt
        self.itemsize = itemsize
        self.w_obj = w_obj

    def getformat(self):
        return self.fmt

    def getitemsize(self):
        return self.itemsize

    def getndim(self):
        return 1

    def getshape(self):
        length =self.getlength()
        if length == 0:
            return [0]
        return [length // self.itemsize]

    def getstrides(self):
        return [self.getitemsize()]

    def new_slice(self, start, step, slicelength):
        if step == 1:
            n = self.itemsize
            newbuf = SubBuffer(self.data, start * n, slicelength * n)
            return RawBufferView(newbuf, self.fmt, self.itemsize, w_obj=self.w_obj)
        else:
            return BufferView.new_slice(self, start, step, slicelength)


class SimpleView(RawBufferView_Base):
    _attrs_ = ['readonly', 'data']
    _immutable_ = True

    def __init__(self, data, w_obj=None):
        self.data = data
        self.readonly = self.data.readonly
        self.w_obj = w_obj

    def getformat(self):
        return 'B'

    def getitemsize(self):
        return 1

    def getndim(self):
        return 1

    def getshape(self):
        return [self.getlength()]

    def getstrides(self):
        return [1]

    def get_offset(self, space, dim, index):
        "Convert index at dimension `dim` into a byte offset"
        assert dim == 0
        nitems = self.getlength()
        if index < 0:
            index += nitems
        if index < 0 or index >= nitems:
            raise oefmt(space.w_IndexError,
                "index out of bounds on dimension %d", dim + 1)
        return index

    def w_getitem(self, space, idx):
        idx = self.get_offset(space, 0, idx)
        ch = self.data[idx]
        return space.newint(ord(ch))

    def new_slice(self, start, step, slicelength):
        if step == 1:
            return SimpleView(SubBuffer(self.data, start, slicelength), w_obj=self.w_obj)
        else:
            return BufferSlice(self, start, step, slicelength, w_obj=self.w_obj)

    def setitem_w(self, space, idx, w_obj):
        idx = self.get_offset(space, 0, idx)
        self.data[idx] = space.byte_w(w_obj)


class BufferSlice(BufferView):
    _immutable_ = True
    _attrs_ = ['parent', 'readonly', 'shape', 'strides', 'start', 'step']

    def __init__(self, parent, start, step, length, w_obj=None):
        self.w_obj = w_obj
        self.parent = parent
        self.readonly = self.parent.readonly
        self.strides = parent.getstrides()[:]
        self.start = start
        self.step = step
        self.strides[0] *= step
        self.shape = parent.getshape()[:]
        self.shape[0] = length

    def getlength(self):
        return self.shape[0] * self.getitemsize()

    def getbytes(self, start, size):
        offset = self.start * self.parent.getstrides()[0]
        return self.parent.getbytes(offset + start, size)

    def setbytes(self, start, string):
        # Unlike getbytes, which always goes through _copy_base,
        # this is directly exposed. It must keep track of weird strides.
        length = len(string)
        if length == 0:
            return        # otherwise, adding self.offset might make 'start'
                          # out of bounds
        elif length > 1 and self.step != 1:
            # We cannot use self.parent.setbytes, we need to roll our own
            # XXX check that length is not too long
            last_stride = self.getstrides()[0]
            itemsize = self.getitemsize()
            assert itemsize >= 0
            offset = self.start * itemsize
            for i in range(length):
                os = offset + i * last_stride
                start = i * itemsize
                self.parent.setbytes(os, string[start:(start+itemsize)])
        else:
            offset = self.start * self.parent.getstrides()[0]
            self.parent.setbytes(offset + start, string)

    def get_raw_address(self):
        from rpython.rtyper.lltypesystem import rffi
        offset = self.start * self.parent.getstrides()[0]
        return rffi.ptradd(self.parent.get_raw_address(), offset)

    def getformat(self):
        return self.parent.getformat()

    def getitemsize(self):
        return self.parent.getitemsize()

    def getndim(self):
        return self.parent.getndim()

    def getshape(self):
        return self.shape

    def getstrides(self):
        return self.strides

    def parent_index(self, idx):
        return self.start + self.step * idx

    def w_getitem(self, space, idx):
        return self.parent.w_getitem(space, self.parent_index(idx))

    def as_readbuf(self):
        if self.step == 1:
            byte_offset = self.start * self.parent.getstrides()[0]
            return SubBuffer(self.parent.as_readbuf(), byte_offset, self.getlength())
        return StringBuffer(self.as_str())

    def as_writebuf(self):
        if self.step != 1:
            raise BufferInterfaceNotFound
        byte_offset = self.start * self.parent.getstrides()[0]
        return SubBuffer(self.parent.as_writebuf(), byte_offset, self.getlength())

    def new_slice(self, start, step, slicelength):
        real_start = self.start + start * self.step
        real_step = self.step * step
        return BufferSlice(self.parent, real_start, real_step, slicelength,
                           w_obj=self.w_obj)

    def setitem_w(self, space, idx, w_obj):
        return self.parent.setitem_w(space, self.parent_index(idx), w_obj)


# XXX not sure this is the right approach, maybe adding a copy to BufferView or
# even a toreadonly would be a better approach

class ReadonlyWrapper(BufferView):
    _immutable_ = True
    def __init__(self, view):
        self.view = view
        self.readonly = True
        self.w_obj = view.w_obj

    def getlength(self):
        return self.view.getlength()

    def as_str(self):
        return self.view.as_str()

    def getbytes(self, start, size):
        return self.view.getbytes(start, size)

    def setbytes(self, start, string):
        assert 0, "should be unreachable"

    def get_raw_address(self):
        return self.view.get_raw_address()

    def as_readbuf(self):
        return self.view.as_readbuf()

    def as_writebuf(self):
        return self.view.as_writebuf()

    def getformat(self):
        return self.view.getformat()

    def getitemsize(self):
        return self.view.getitemsize()

    def getndim(self):
        return self.view.getndim()

    def getshape(self):
        return self.view.getshape()

    def getstrides(self):
        return self.view.getstrides()

    def releasebuffer(self):
        return self.view.releasebuffer()

    def new_slice(self, start, step, slicelength):
        return ReadonlyWrapper(BufferSlice(self, start, step, slicelength, w_obj=self.w_obj))


class NonOwningReleaseView(BufferView):
    """Wraps a BufferView but with a no-op releasebuffer.

    Used when handing out a BufferView from an object that already owns
    the underlying export (e.g. memoryview(bytearray) returning its
    internal view).  The memoryview's own finalizer is responsible for
    calling releasebuffer on the wrapped view exactly once; callers that
    go through buffer_w must not also decrement the shared _exports
    counter.
    """
    _immutable_ = True

    def __init__(self, view):
        self.view = view
        self.readonly = view.readonly
        self.w_obj = view.w_obj

    def getlength(self):
        return self.view.getlength()

    def as_str(self):
        return self.view.as_str()

    def getbytes(self, start, size):
        return self.view.getbytes(start, size)

    def setbytes(self, start, string):
        return self.view.setbytes(start, string)

    def get_raw_address(self):
        return self.view.get_raw_address()

    def as_readbuf(self):
        return self.view.as_readbuf()

    def as_writebuf(self):
        return self.view.as_writebuf()

    def getformat(self):
        return self.view.getformat()

    def getitemsize(self):
        return self.view.getitemsize()

    def getndim(self):
        return self.view.getndim()

    def getshape(self):
        return self.view.getshape()

    def getstrides(self):
        return self.view.getstrides()

    def releasebuffer(self):
        # no-op: the owning memoryview is responsible for releasing.
        pass

    def new_slice(self, start, step, slicelength):
        return NonOwningReleaseView(self.view.new_slice(start, step, slicelength))


class DunderReleaseView(NonOwningReleaseView):
    """Wraps the BufferView obtained from a memoryview returned by a
    Python-level __buffer__ override (PEP 688).  On release:

    1. Notifies: calls the exporter's __release_buffer__(mv), passing
       back the same memoryview that __buffer__ returned.  w_base_type
       (may be None) is the builtin type, if any, that provides a
       *default* __release_buffer__ for this exporter (e.g. bytearray);
       CPython only invokes __release_buffer__ when it resolves to a
       genuine Python-level override below that builtin, since calling a
       builtin's own default automatically (nothing was actually
       overridden) would wrongly complain about an unrelated buffer
       whenever only __buffer__ was overridden to return something else.
       w_base_type=None (the generic case, e.g. plain objects) always
       invokes whatever is found.
    2. Force-releases mv, but only when it genuinely wraps the exporter's
       own buffer (mv.obj is w_exporter): CPython does this regardless of
       what step 1's __release_buffer__ override did (even if it never
       calls super()), so a builtin exporter's own invariants (e.g.
       bytearray's resize lock) stay balanced.  When mv wraps something
       else entirely, nothing is force-released -- the exporter/override
       is fully responsible for that buffer's lifetime.

    buffer_is_default indicates __buffer__ itself is just the builtin
    default (not a genuine Python-level override): only then is mv
    marked .restricted for the duration of the __release_buffer__ call,
    forbidding new buffer exports from it (CPython does the same only
    when it had to synthesize mv itself, rather than handing back
    whatever a real __buffer__ override returned).
    """
    _immutable_ = True

    def __init__(self, view, space, w_exporter, w_mv, w_base_type=None,
                 buffer_is_default=False):
        NonOwningReleaseView.__init__(self, view)
        self.space = space
        self.w_exporter = w_exporter
        self.w_mv = w_mv
        self.w_base_type = w_base_type
        self.buffer_is_default = buffer_is_default

    def releasebuffer(self):
        space = self.space
        w_exporter = self.w_exporter
        w_mv = self.w_mv
        w_impl = space.lookup(w_exporter, '__release_buffer__')
        if w_impl is not None:
            from pypy.objspace.std.memoryobject import W_MemoryView
            assert isinstance(w_mv, W_MemoryView)
            w_base_type = self.w_base_type
            if (w_base_type is None or
                    # Equivalent to space.is_overloaded() but for a non-constant type
                    w_impl is not space.lookup_in_type(w_base_type,
                                        '__release_buffer__')):
                if self.buffer_is_default:
                    w_mv.restricted = True
                try:
                    space.get_and_call_function(w_impl, w_exporter, w_mv)
                finally:
                    w_mv.restricted = False
        try:
            owns_match = space.getattr(w_mv, space.newtext('obj')) is w_exporter
        except OperationError as e:
            if not e.match(space, space.w_ValueError):
                raise
            owns_match = False
        if owns_match:
            space.call_method(w_mv, 'release')

