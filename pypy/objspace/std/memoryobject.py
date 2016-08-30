"""
Implementation of the 'buffer' and 'memoryview' types.
"""
import operator

from rpython.rlib.buffer import Buffer, SubBuffer
from rpython.rlib.objectmodel import compute_hash
from rpython.rlib.rstruct.error import StructError
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty,  make_weakref_descr
from pypy.module.struct.formatiterator import UnpackFormatIterator, PackFormatIterator
from pypy.objspace.std.bytesobject import getbytevalue
from rpython.rlib.unroll import unrolling_iterable

MEMORYVIEW_MAX_DIM = 64
MEMORYVIEW_SCALAR   = 0x0001
MEMORYVIEW_C        = 0x0002
MEMORYVIEW_FORTRAN  = 0x0004
MEMORYVIEW_SCALAR   = 0x0008
MEMORYVIEW_PIL      = 0x0010


class W_MemoryView(W_Root):
    """Implement the built-in 'memoryview' type as a wrapper around
    an interp-level buffer.
    """

    def __init__(self, buf, format=None, itemsize=1, ndim=-1,
                 shape=None, strides=None, suboffsets=None):
        assert isinstance(buf, Buffer)
        self.buf = buf
        self._hash = -1
        # private copies of format, shape, itemsize, ... on this class
        self.format = format
        self.itemsize = itemsize
        self.shape = shape
        self.strides = strides
        self.suboffsets = suboffsets
        self.ndim = ndim
        self.flags = 0
        self.length = -1
        self._init_flags()

    # several fields are "overwritten" by the memory view (shape, strides, ...)
    # thus use only those getter fields instead of directly accessing the fields
    def getndim(self):
        if self.ndim == -1:
            return self.buf.getndim()
        return self.ndim

    def getshape(self):
        if self.shape is None:
            return self.buf.getshape()
        return self.shape

    def getstrides(self):
        if self.strides is None:
            return self.buf.getstrides()
        return self.strides

    def getitemsize(self):
        return self.itemsize

    # memoryview needs to modify the field 'format', to prevent the modification
    # of the buffer, we save the new format here!
    def getformat(self):
        if self.format is None:
            return self.buf.getformat()
        return self.format

    def setformat(self, value):
        self.format = value

    def buffer_w_ex(self, space, flags):
        self._check_released(space)
        space.check_buf_flags(flags, self.buf.readonly)
        return self.buf, self.getformat(), self.itemsize

    @staticmethod
    def descr_new_memoryview(space, w_subtype, w_object):
        return W_MemoryView(*space.buffer_w_ex(w_object, space.BUF_FULL_RO))

    def _make_descr__cmp(name):
        def descr__cmp(self, space, w_other):
            if self.buf is None:
                return space.wrap(getattr(operator, name)(self, w_other))
            if isinstance(w_other, W_MemoryView):
                # xxx not the most efficient implementation
                str1 = self.as_str()
                str2 = w_other.as_str()
                return space.wrap(getattr(operator, name)(str1, str2))

            try:
                buf = space.buffer_w(w_other, space.BUF_CONTIG_RO)
            except OperationError as e:
                if not e.match(space, space.w_TypeError):
                    raise
                return space.w_NotImplemented
            else:
                str1 = self.as_str()
                str2 = buf.as_str()
                return space.wrap(getattr(operator, name)(str1, str2))
        descr__cmp.func_name = name
        return descr__cmp

    descr_eq = _make_descr__cmp('eq')
    descr_ne = _make_descr__cmp('ne')

    def as_str(self):
        return ''.join(self.copy_buffer())

    def copy_buffer(self):
        buf = self.buf
        n_bytes = buf.getlength()
        data = []
        self._copy_rec(0, data, 0)
        return data

    def _copy_rec(self, idim, data, off):
        shapes = self.getshape()
        shape = shapes[idim]
        strides = self.getstrides()

        if self.getndim()-1 == idim:
            self._copy_base(data,off)
            return

        # TODO add a test that has at least 2 dims
        for i in range(shape):
            self._copy_rec(idim+1,data,off)
            off += strides[idim]

    def _copy_base(self, data, off):
        shapes = self.getshape()
        step = shapes[0]
        strides = self.getstrides()
        itemsize = self.getitemsize()
        for i in range(step):
            bytes = self.buf.getslice(off, off+itemsize, 1, itemsize)
            data.append(bytes)
            off += strides[0]
            # do notcopy data if the sub buffer is out of bounds
            if off >= self.buf.getlength():
                break

    def getlength(self):
        if self.length != -1:
            return self.length // self.itemsize
        return self.buf.getlength() // self.itemsize

    def descr_tobytes(self, space):
        self._check_released(space)
        return space.newbytes(self.as_str())

    def descr_tolist(self, space):
        self._check_released(space)

        buf = self.buf
        dim = self.getndim()
        fmt = self.getformat()
        if dim == 0:
            raise NotImplementedError
        elif dim == 1:
            itemsize = self.getitemsize()
            return self._tolist(space, buf, buf.getlength() // itemsize, fmt)
        else:
            return self._tolist_rec(space, buf, 0, 0, fmt)

    def _tolist(self, space, buf, count, fmt):
        # TODO: this probably isn't very fast
        fmtiter = UnpackFormatIterator(space, buf)
        fmtiter.interpret(fmt * count)
        return space.newlist(fmtiter.result_w)

    def _tolist_rec(self, space, buf, start, idim, fmt):
        strides = self.getstrides()
        shape = self.getshape()
        #
        dim = idim+1
        stride = strides[idim]
        itemsize = self.getitemsize()
        dimshape = shape[idim]
        #
        if dim >= self.getndim():
            bytecount = (stride * dimshape)
            count = bytecount // itemsize
            return self._tolist(space, buf, count, fmt)
        items = [None] * dimshape

        for i in range(dimshape):
            item = self._tolist_rec(space, SubBuffer(buf, start, stride), start, idim+1, fmt)
            items[i] = item
            start += stride

        return space.newlist(items)


    def _start_from_tuple(self, space, w_tuple):
        from pypy.objspace.std.tupleobject import W_TupleObject
        start = 0

        view = self.buf
        length = space.len_w(w_tuple)
        dim = view.getndim()
        dim = 0
        assert isinstance(w_tuple, W_TupleObject)
        while dim < length:
            w_obj = w_tuple.getitem(space, dim)
            index = w_obj.int_w(space)
            start = self.lookup_dimension(space, start, dim, index)
            dim += 1
        return start

    def lookup_dimension(self, space, start, dim, index):
        view = self.buf
        shape = view.getshape()
        strides = view.getstrides()
        nitems = shape[dim]
        if index < 0:
            index += nitems
        if index < 0 or index >= nitems:
            raise oefmt(space.w_IndexError,
                "index out of bounds on dimension %d", dim+1)
        start += strides[dim] * index
        # TODO suboffsets?
        return start

    def _getitem_tuple_indexed(self, space, w_index):
        view = self.buf

        fmt = view.getformat() # TODO adjust format?

        length = space.len_w(w_index)
        ndim = view.getndim()
        if length < ndim:
            raise OperationError(space.w_NotImplementedError, \
                    space.wrap("sub-views are not implemented"))

        if length > ndim:
            raise oefmt(space.w_TypeError, \
                    "cannot index %d-dimension view with %d-element tuple",
                    length, ndim)

        start = self._start_from_tuple(space, w_index)

        buf = SubBuffer(self.buf, start, view.getitemsize())
        fmtiter = UnpackFormatIterator(space, buf)
        fmtiter.interpret(fmt)
        return fmtiter.result_w[0]


    def descr_getitem(self, space, w_index):
        self._check_released(space)

        if space.isinstance_w(w_index, space.w_tuple):
            return self._getitem_tuple_indexed(space, w_index)

        start, stop, step, size = space.decode_index4(w_index, self.getlength())
        # ^^^ for a non-slice index, this returns (index, 0, 0, 1)
        itemsize = self.getitemsize()
        start, stop, size = self._apply_itemsize(space, start, size, itemsize)
        if step == 0:  # index only
            if itemsize == 1:
                ch = self.buf.getitem(start)
                return space.newint(ord(ch))
            else:
                # TODO: this probably isn't very fast
                buf = SubBuffer(self.buf, start, itemsize)
                fmtiter = UnpackFormatIterator(space, buf)
                fmtiter.interpret(self.format)
                return fmtiter.result_w[0]
        elif step == 1:
            mv = W_MemoryView.copy(self)
            mv.slice(start, stop, step, size)
            mv._init_flags()
            return mv
        else:
            mv = W_MemoryView.copy(self)
            mv.slice(start, stop, step, size)
            mv.length = mv.bytecount_from_shape()
            mv._init_flags()
            return mv

    def slice(self, start, stop, step, size):
        # modifies the buffer, shape and stride to allow step to be > 1
        # NOTE that start, stop & size are already byte offsets/count
        # TODO subbuffer
        strides = self.getstrides()[:]
        shape = self.getshape()[:]
        itemsize = self.getitemsize()
        dim = 0
        self.buf = SubBuffer(self.buf, strides[dim] * (start//itemsize), size*step)
        shape[dim] = size
        strides[dim] = strides[dim] * step
        self.strides = strides
        self.shape = shape

    def bytecount_from_shape(self):
        dim = self.getndim()
        shape = self.getshape()
        length = 1
        for i in range(dim):
            length *= shape[i]
        return length * self.getitemsize()

    @staticmethod
    def copy(view, buf=None):
        # TODO suboffsets
        if buf == None:
            buf = view.buf
        return W_MemoryView(buf, view.getformat(), view.getitemsize(),
                            view.getndim(), view.getshape()[:], view.getstrides()[:])

    def _apply_itemsize(self, space, start, size, itemsize):
        if itemsize > 1:
            start *= itemsize
            size *= itemsize

        stop  = start + size
        # start & stop are now byte offset, thus use self.buf.getlength()
        if stop > self.buf.getlength():
            raise oefmt(space.w_IndexError, 'index out of range')

        return start, stop, size

    def descr_setitem(self, space, w_index, w_obj):
        self._check_released(space)
        if self.buf.readonly:
            raise oefmt(space.w_TypeError, "cannot modify read-only memory")
        if space.isinstance_w(w_index, space.w_tuple):
            raise oefmt(space.w_NotImplementedError, "")
        start, stop, step, size = space.decode_index4(w_index, self.getlength())
        itemsize = self.getitemsize()
        start, stop, size = self._apply_itemsize(space, start, size, itemsize)
        if step == 0:  # index only
            if itemsize == 1:
                ch = getbytevalue(space, w_obj)
                self.buf.setitem(start, ch)
            else:
                # TODO: this probably isn't very fast
                fmtiter = PackFormatIterator(space, [w_obj], itemsize)
                try:
                    fmtiter.interpret(self.format)
                except StructError as e:
                    raise oefmt(space.w_TypeError,
                                "memoryview: invalid type for format '%s'",
                                self.format)
                self.buf.setslice(start, fmtiter.result.build())
        elif step == 1:
            value = space.buffer_w(w_obj, space.BUF_CONTIG_RO)
            if value.getlength() != size:
                raise oefmt(space.w_ValueError,
                            "cannot modify size of memoryview object")
            self.buf.setslice(start, value.as_str())
        else:
            if self.getndim() != 1:
                raise oefmt(space.w_NotImplementedError,
                        "memoryview slice assignments are currently "
                        "restricted to ndim = 1")
            # this is the case of a one dimensional copy!
            # NOTE we could maybe make use of copy_base, but currently we do not
            itemsize = self.getitemsize()
            data = []
            src = space.buffer_w(w_obj, space.BUF_CONTIG_RO)
            dst_strides = self.getstrides()
            dim = 0
            dst = SubBuffer(self.buf, start, size)
            src_stride0 = dst_strides[dim]

            off = 0
            src_shape0 = size // itemsize
            src_stride0 = src.getstrides()[0]
            if isinstance(w_obj, W_MemoryView):
                src_stride0 = w_obj.getstrides()[0]
            for i in range(src_shape0):
                data.append(src.getslice(off,off+itemsize,1,itemsize))
                off += src_stride0
            off = 0
            dst_stride0 = self.getstrides()[0] * step
            for dataslice in data:
                dst.setslice(off, dataslice)
                off += dst_stride0

    def descr_len(self, space):
        self._check_released(space)
        return space.wrap(self.getlength())

    def w_get_format(self, space):
        self._check_released(space)
        return space.wrap(self.getformat())

    def w_get_itemsize(self, space):
        self._check_released(space)
        return space.wrap(self.itemsize)

    def w_get_ndim(self, space):
        self._check_released(space)
        return space.wrap(self.buf.getndim())

    def w_is_readonly(self, space):
        self._check_released(space)
        return space.newbool(bool(self.buf.readonly))

    def w_get_shape(self, space):
        self._check_released(space)
        return space.newtuple([space.wrap(x) for x in self.getshape()])

    def w_get_strides(self, space):
        self._check_released(space)
        return space.newtuple([space.wrap(x) for x in self.getstrides()])

    def w_get_suboffsets(self, space):
        self._check_released(space)
        # I've never seen anyone filling this field
        return space.newtuple([])

    def descr_repr(self, space):
        if self.buf is None:
            return self.getrepr(space, u'released memory')
        else:
            return self.getrepr(space, u'memory')

    def descr_hash(self, space):
        if self._hash == -1:
            self._check_released(space)
            if not self.buf.readonly:
                raise oefmt(space.w_ValueError,
                            "cannot hash writable memoryview object")
            self._hash = compute_hash(self.buf.as_str())
        return space.wrap(self._hash)

    def descr_release(self, space):
        self.buf = None

    def _check_released(self, space):
        if self.buf is None:
            raise oefmt(space.w_ValueError,
                        "operation forbidden on released memoryview object")

    def descr_enter(self, space):
        self._check_released(space)
        return self

    def descr_exit(self, space, __args__):
        self.buf = None
        return space.w_None

    def descr_pypy_raw_address(self, space):
        from rpython.rtyper.lltypesystem import lltype, rffi
        try:
            ptr = self.buf.get_raw_address()
        except ValueError:
            # report the error using the RPython-level internal repr of self.buf
            msg = ("cannot find the underlying address of buffer that "
                   "is internally %r" % (self.buf,))
            raise OperationError(space.w_ValueError, space.wrap(msg))
        return space.wrap(rffi.cast(lltype.Signed, ptr))

    def get_native_fmtchar(self, fmt):
        from rpython.rtyper.lltypesystem import rffi
        size = -1
        if fmt[0] == '@':
            f = fmt[1]
        else:
            f = fmt[0]
        if f == 'c' or f == 'b' or f == 'B':
            size = rffi.sizeof(rffi.CHAR)
        elif f == 'h' or f == 'H':
            size = rffi.sizeof(rffi.SHORT)
        elif f == 'i' or f == 'I':
            size = rffi.sizeof(rffi.INT)
        elif f == 'l' or f == 'L':
            size = rffi.sizeof(rffi.LONG)
        elif f == 'q' or f == 'Q':
            size = rffi.sizeof(rffi.LONGLONG)
        elif f == 'n' or f == 'N':
            size = rffi.sizeof(rffi.SIZE_T)
        elif f == 'f':
            size = rffi.sizeof(rffi.FLOAT)
        elif f == 'd':
            size = rffi.sizeof(rffi.DOUBLE)
        elif f == '?':
            size = rffi.sizeof(rffi.CHAR)
        elif f == 'P':
            size = rffi.sizeof(rffi.VOIDP)
        return size

    def _zero_in_shape(self):
        # this method could be moved to the class Buffer
        buf = self.buf
        shape = buf.getshape()
        for i in range(buf.getndim()):
            if shape[i] == 0:
                return True
        return False

    def descr_cast(self, space, w_format, w_shape=None):
        self._check_released(space)

        if not space.isinstance_w(w_format, space.w_unicode):
            raise OperationError(space.w_TypeError, \
                    space.wrap("memoryview: format argument must be a string"))

        fmt = space.str_w(w_format)
        buf = self.buf
        ndim = 1

        if not memory_view_c_contiguous(space, self.flags):
            raise OperationError(space.w_TypeError, \
                    space.wrap("memoryview: casts are restricted" \
                               " to C-contiguous views"))

        if (w_shape or buf.getndim() != 1) and self._zero_in_shape():
            raise OperationError(space.w_TypeError, \
                    space.wrap("memoryview: cannot casts view with" \
                               " zeros in shape or strides"))

        itemsize = self.get_native_fmtchar(fmt)
        if w_shape:
            if not (space.isinstance_w(w_shape, space.w_list) or space.isinstance_w(w_shape, space.w_tuple)):
                raise oefmt(space.w_TypeError, "expected list or tuple got %T", w_shape)
            ndim = space.len_w(w_shape)
            if ndim > MEMORYVIEW_MAX_DIM:
                raise oefmt(space.w_ValueError, \
                        "memoryview: number of dimensions must not exceed %d",
                        ndim)
            # yes access ndim as field
            if self.ndim > 1 and buf.getndim() != 1:
                raise OperationError(space.w_TypeError, \
                    space.wrap("memoryview: cast must be 1D -> ND or ND -> 1D"))

        mv = W_MemoryView(buf, self.format, self.itemsize)
        origfmt = mv.getformat()
        mv._cast_to_1D(space, origfmt, fmt, itemsize)
        if w_shape:
            fview = space.fixedview(w_shape)
            shape = [space.int_w(w_obj) for w_obj in fview]
            mv._cast_to_ND(space, shape, ndim)
        return mv

    def _init_flags(self):
        buf = self.buf
        ndim = buf.getndim()
        flags = 0
        if ndim == 0:
            flags |= MEMORYVIEW_SCALAR | MEMORYVIEW_C | MEMORYVIEW_FORTRAN
        if ndim == 1:
            shape = buf.getshape()
            strides = buf.getstrides()
            if len(shape) > 0 and shape[0] == 1 and \
               len(strides) > 0 and strides[0] == buf.getitemsize():
                flags |= MEMORYVIEW_C | MEMORYVIEW_SCALAR
        # TODO for now?
        flags |= MEMORYVIEW_C
        # TODO if buf.is_contiguous('C'):
        # TODO     flags |= MEMORYVIEW_C
        # TODO elif buf.is_contiguous('F'):
        # TODO     flags |= MEMORYVIEW_FORTRAN

        # TODO missing suboffsets

        self.flags = flags

    def _cast_to_1D(self, space, origfmt, fmt, itemsize):
        buf = self.buf
        if itemsize < 0:
            raise oefmt(space.w_ValueError, "memoryview: destination" \
                    " format must be a native single character format prefixed" \
                    " with an optional '@'")

        if self.get_native_fmtchar(origfmt) < 0 or \
           (not is_byte_format(fmt) and not is_byte_format(origfmt)):
            raise oefmt(space.w_TypeError,
                    "memoryview: cannot cast between" \
                    " two non-byte formats")

        if buf.getlength() % itemsize != 0:
            raise oefmt(space.w_TypeError,
                    "memoryview: length is not a multiple of itemsize")

        newfmt = self.get_native_fmtstr(fmt)
        if not newfmt:
            raise oefmt(space.w_RuntimeError,
                    "memoryview: internal error")
        self.format = newfmt
        self.itemsize = itemsize
        self.ndim = 1
        self.shape = [buf.getlength() // itemsize]
        self.strides = [itemsize]
        # XX suboffsets

        self._init_flags()

    def get_native_fmtstr(self, fmt):
        lenfmt = len(fmt)
        nat = False
        if lenfmt == 0:
            return None
        elif lenfmt == 1:
            format = fmt[0] # fine!
        elif lenfmt == 2:
            if fmt[0] == '@':
                nat = True
                format = fmt[1]
            else:
                return None
        else:
            return None

        chars = ['c','b','B','h','H','i','I','l','L','q',
                 'Q','n','N','f','d','?','P']
        for c in unrolling_iterable(chars):
            if c == format:
                if nat: return '@'+c
                else: return c

        return None

    def _cast_to_ND(self, space, shape, ndim):
        buf = self.buf

        self.ndim = ndim
        length = self.itemsize
        if ndim == 0:
            self.shape = []
            self.strides = []
        else:
            self.shape = shape
            for i in range(ndim):
                length *= shape[i]
            self._init_strides_from_shape()

        if length != self.buf.getlength():
            raise OperationError(space.w_TypeError,
                    space.wrap("memoryview: product(shape) * itemsize != buffer size"))

        self._init_flags()

    def _init_strides_from_shape(self):
        shape = self.getshape()
        s = [0] * len(shape)
        self.strides = s
        ndim = self.getndim()
        s[ndim-1] = self.itemsize
        i = ndim-2
        while i >= 0:
            s[i] = s[i+1] * shape[i+1]
            i -= 1

    def descr_hex(self, space):
        from pypy.objspace.std.bytearrayobject import _array_to_hexstring
        self._check_released(space)
        return _array_to_hexstring(space, self.buf)

def is_byte_format(char):
    return char == 'b' or char == 'B' or char == 'c'

def memory_view_c_contiguous(space, flags):
    return flags & (space.BUF_CONTIG_RO|MEMORYVIEW_C) != 0

W_MemoryView.typedef = TypeDef(
    "memoryview",
    __doc__ = """\
Create a new memoryview object which references the given object.
""",
    __new__     = interp2app(W_MemoryView.descr_new_memoryview),
    __eq__      = interp2app(W_MemoryView.descr_eq),
    __getitem__ = interp2app(W_MemoryView.descr_getitem),
    __len__     = interp2app(W_MemoryView.descr_len),
    __ne__      = interp2app(W_MemoryView.descr_ne),
    __setitem__ = interp2app(W_MemoryView.descr_setitem),
    __repr__    = interp2app(W_MemoryView.descr_repr),
    __hash__      = interp2app(W_MemoryView.descr_hash),
    __enter__   = interp2app(W_MemoryView.descr_enter),
    __exit__    = interp2app(W_MemoryView.descr_exit),
    __weakref__ = make_weakref_descr(W_MemoryView),
    cast        = interp2app(W_MemoryView.descr_cast),
    hex         = interp2app(W_MemoryView.descr_hex),
    tobytes     = interp2app(W_MemoryView.descr_tobytes),
    tolist      = interp2app(W_MemoryView.descr_tolist),
    release     = interp2app(W_MemoryView.descr_release),
    format      = GetSetProperty(W_MemoryView.w_get_format),
    itemsize    = GetSetProperty(W_MemoryView.w_get_itemsize),
    ndim        = GetSetProperty(W_MemoryView.w_get_ndim),
    readonly    = GetSetProperty(W_MemoryView.w_is_readonly),
    shape       = GetSetProperty(W_MemoryView.w_get_shape),
    strides     = GetSetProperty(W_MemoryView.w_get_strides),
    suboffsets  = GetSetProperty(W_MemoryView.w_get_suboffsets),
    _pypy_raw_address = interp2app(W_MemoryView.descr_pypy_raw_address),
    )
W_MemoryView.typedef.acceptable_as_base_class = False
