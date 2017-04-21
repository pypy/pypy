"""
Implementation of the 'memoryview' type.
"""
import operator

from rpython.rlib.objectmodel import compute_hash
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import PyBuffer, SimpleBuffer, SubBuffer
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty,  make_weakref_descr
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import always_inline

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

    def __init__(self, buf):
        assert isinstance(buf, PyBuffer)
        self.buf = buf
        self._hash = -1
        self.flags = 0
        self._init_flags()

    def getndim(self):
        return self.buf.getndim()

    def getshape(self):
        return self.buf.getshape()

    def getstrides(self):
        return self.buf.getstrides()

    def getitemsize(self):
        return self.buf.getitemsize()

    def getformat(self):
        return self.buf.getformat()

    def buffer_w(self, space, flags):
        self._check_released(space)
        space.check_buf_flags(flags, self.buf.readonly)
        return self.buf

    @staticmethod
    def descr_new_memoryview(space, w_subtype, w_object):
        if isinstance(w_object, W_MemoryView):
            w_object._check_released(space)
            return W_MemoryView.copy(w_object)
        buf = space.buffer_w(w_object, space.BUF_FULL_RO)
        return W_MemoryView(buf)

    def _make_descr__cmp(name):
        def descr__cmp(self, space, w_other):
            if self.buf is None:
                return space.newbool(getattr(operator, name)(self, w_other))
            if isinstance(w_other, W_MemoryView):
                # xxx not the most efficient implementation
                str1 = self.buf.as_str()
                str2 = w_other.buf.as_str()
                return space.newbool(getattr(operator, name)(str1, str2))

            try:
                buf = space.buffer_w(w_other, space.BUF_CONTIG_RO)
            except OperationError as e:
                if not e.match(space, space.w_TypeError):
                    raise
                return space.w_NotImplemented
            else:
                str1 = self.buf.as_str()
                str2 = buf.as_str()
                return space.newbool(getattr(operator, name)(str1, str2))
        descr__cmp.func_name = name
        return descr__cmp

    descr_eq = _make_descr__cmp('eq')
    descr_ne = _make_descr__cmp('ne')

    def getlength(self):
        return self.buf.getlength()

    def descr_tobytes(self, space):
        self._check_released(space)
        return space.newbytes(self.buf.as_str())

    def descr_tolist(self, space):
        self._check_released(space)
        return self.buf.w_tolist(space)

    def _start_from_tuple(self, space, w_tuple):
        from pypy.objspace.std.tupleobject import W_AbstractTupleObject
        start = 0

        view = self.buf
        length = space.len_w(w_tuple)
        dim = view.getndim()
        dim = 0
        assert isinstance(w_tuple, W_AbstractTupleObject)
        while dim < length:
            w_obj = w_tuple.getitem(space, dim)
            index = space.getindex_w(w_obj, space.w_IndexError)
            start += self.buf.get_offset(space, dim, index)
            dim += 1
        return start

    def _getitem_tuple_indexed(self, space, w_index):
        view = self.buf

        fmt = view.getformat() # TODO adjust format?

        length = space.len_w(w_index)
        ndim = view.getndim()
        if length < ndim:
            raise oefmt(space.w_NotImplementedError,
                        "sub-views are not implemented")

        if length > ndim:
            raise oefmt(space.w_TypeError, \
                    "cannot index %d-dimension view with %d-element tuple",
                    length, ndim)

        start = self._start_from_tuple(space, w_index)
        itemsize = self.getitemsize()
        data = view.getbytes(start, itemsize)
        return view.value_from_bytes(space, data)

    def _decode_index(self, space, w_index, is_slice):
        shape = self.getshape()
        if len(shape) == 0:
            count = 1
        else:
            count = shape[0]
        return space.decode_index4(w_index, count)

    def descr_getitem(self, space, w_index):
        self._check_released(space)

        if space.isinstance_w(w_index, space.w_tuple):
            return self._getitem_tuple_indexed(space, w_index)
        is_slice = space.isinstance_w(w_index, space.w_slice)
        start, stop, step, slicelength = self._decode_index(space, w_index, is_slice)
        # ^^^ for a non-slice index, this returns (index, 0, 0, 1)
        if step == 0:  # index only
            itemsize = self.getitemsize()
            dim = self.getndim()
            if dim == 0:
                raise oefmt(space.w_TypeError, "invalid indexing of 0-dim memory")
            elif dim == 1:
                return self.buf.w_getitem(space, start)
            else:
                raise oefmt(space.w_NotImplementedError, "multi-dimensional sub-views are not implemented")
        elif is_slice:
            return self.new_slice(start, stop, step, slicelength, 0)
        # multi index is handled at the top of this function
        else:
            raise TypeError("memoryview: invalid slice key")

    def new_slice(self, start, stop, step, slicelength, dim):
        if step == 1 and isinstance(self.buf, SimpleBuffer):
            sliced = SimpleBuffer(SubBuffer(self.buf.data, start, slicelength))
        else:
            sliced = BufferSlice(self.buf, start, step, slicelength)
        return W_MemoryView(sliced)

    def init_len(self):
        self.length = self.bytecount_from_shape()

    def bytecount_from_shape(self):
        dim = self.getndim()
        shape = self.getshape()
        length = 1
        for i in range(dim):
            length *= shape[i]
        return length * self.getitemsize()

    @staticmethod
    def copy(view):
        # TODO suboffsets
        buf = view.buf
        return W_MemoryView(buf)

    def descr_setitem(self, space, w_index, w_obj):
        self._check_released(space)
        if self.buf.readonly:
            raise oefmt(space.w_TypeError, "cannot modify read-only memory")
        if space.isinstance_w(w_index, space.w_tuple):
            raise oefmt(space.w_NotImplementedError, "")
        start, stop, step, size = space.decode_index4(w_index, self.getlength())
        is_slice = space.isinstance_w(w_index, space.w_slice)
        start, stop, step, slicelength = self._decode_index(space, w_index, is_slice)
        itemsize = self.getitemsize()
        if step == 0:  # index only
            self.buf.setitem_w(space, start, w_obj)
        elif step == 1:
            value = space.buffer_w(w_obj, space.BUF_CONTIG_RO)
            if value.getlength() != slicelength * itemsize:
                raise oefmt(space.w_ValueError,
                            "cannot modify size of memoryview object")
            self.buf.setbytes(start * itemsize, value.as_str())
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
            dst = SubBuffer(
                self.buf.as_binary_rw(),
                start * itemsize, slicelength * itemsize)
            src_stride0 = dst_strides[dim]

            off = 0
            src_shape0 = slicelength
            src_stride0 = src.getstrides()[0]
            for i in range(src_shape0):
                data.append(src.getbytes(off, itemsize))
                off += src_stride0
            off = 0
            dst_stride0 = self.getstrides()[0] * step
            for dataslice in data:
                dst.setslice(off, dataslice)
                off += dst_stride0

    def descr_len(self, space):
        self._check_released(space)
        dim = self.getndim()
        if dim == 0:
            return space.newint(1)
        shape = self.getshape()
        return space.newint(shape[0])

    def w_get_nbytes(self, space):
        self._check_released(space)
        return space.newint(self.getlength())

    def w_get_format(self, space):
        self._check_released(space)
        return space.newtext(self.getformat())

    def w_get_itemsize(self, space):
        self._check_released(space)
        return space.newint(self.getitemsize())

    def w_get_ndim(self, space):
        self._check_released(space)
        return space.newint(self.getndim())

    def w_is_readonly(self, space):
        self._check_released(space)
        return space.newbool(bool(self.buf.readonly))

    def w_get_shape(self, space):
        self._check_released(space)
        return space.newtuple([space.newint(x) for x in self.getshape()])

    def w_get_strides(self, space):
        self._check_released(space)
        return space.newtuple([space.newint(x) for x in self.getstrides()])

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
        return space.newint(self._hash)

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
            raise OperationError(space.w_ValueError, space.newtext(msg))
        return space.newint(rffi.cast(lltype.Signed, ptr))

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
        # this method could be moved to the class PyBuffer
        buf = self.buf
        shape = buf.getshape()
        for i in range(buf.getndim()):
            if shape[i] == 0:
                return True
        return False

    def descr_cast(self, space, w_format, w_shape=None):
        self._check_released(space)

        if not space.isinstance_w(w_format, space.w_unicode):
            raise oefmt(space.w_TypeError,
                        "memoryview: format argument must be a string")

        fmt = space.text_w(w_format)
        buf = self.buf
        ndim = 1

        if not memory_view_c_contiguous(space, self.flags):
            raise oefmt(space.w_TypeError,
                        "memoryview: casts are restricted"
                        " to C-contiguous views")

        if (w_shape or buf.getndim() != 1) and self._zero_in_shape():
            raise oefmt(space.w_TypeError,
                        "memoryview: cannot casts view with"
                        " zeros in shape or strides")

        if w_shape:
            if not (space.isinstance_w(w_shape, space.w_list) or space.isinstance_w(w_shape, space.w_tuple)):
                raise oefmt(space.w_TypeError, "expected list or tuple got %T", w_shape)
            ndim = space.len_w(w_shape)
            if ndim > MEMORYVIEW_MAX_DIM:
                raise oefmt(space.w_ValueError, \
                        "memoryview: number of dimensions must not exceed %d",
                        ndim)
            if ndim > 1 and buf.getndim() != 1:
                raise oefmt(space.w_TypeError,
                            "memoryview: cast must be 1D -> ND or ND -> 1D")

        newbuf = self._cast_to_1D(space, buf, fmt)
        if w_shape:
            fview = space.fixedview(w_shape)
            shape = [space.int_w(w_obj) for w_obj in fview]
            newbuf = self._cast_to_ND(space, newbuf, shape, ndim)
        mv = W_MemoryView(newbuf)
        return mv

    def _init_flags(self):
        buf = self.buf
        ndim = self.getndim()
        flags = 0
        if ndim == 0:
            flags |= MEMORYVIEW_SCALAR | MEMORYVIEW_C | MEMORYVIEW_FORTRAN
        elif ndim == 1:
            shape = self.getshape()
            strides = self.getstrides()
            if shape[0] == 1 or strides[0] == self.getitemsize():
                flags |= MEMORYVIEW_C | MEMORYVIEW_FORTRAN
        else:
            ndim = self.getndim()
            shape = self.getshape()
            strides = self.getstrides()
            itemsize = self.getitemsize()
            if PyBuffer_isContiguous(None, ndim, shape, strides,
                                      itemsize, 'C'):
                flags |= MEMORYVIEW_C
            if PyBuffer_isContiguous(None, ndim, shape, strides,
                                      itemsize, 'F'):
                flags |= MEMORYVIEW_FORTRAN

        if False:  # TODO missing suboffsets
            flags |= MEMORYVIEW_PIL
            flags &= ~(MEMORYVIEW_C|MEMORYVIEW_FORTRAN)

        self.flags = flags

    def _cast_to_1D(self, space, buf, fmt):
        itemsize = self.get_native_fmtchar(fmt)
        if itemsize < 0:
            raise oefmt(space.w_ValueError, "memoryview: destination" \
                    " format must be a native single character format prefixed" \
                    " with an optional '@'")

        origfmt = buf.getformat()
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
        return BufferView1D(buf, newfmt, itemsize)

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
                if nat:
                    return '@'+c
                else:
                    return c

        return None

    def _cast_to_ND(self, space, buf, shape, ndim):
        length = itemsize = buf.getitemsize()
        for i in range(ndim):
            length *= shape[i]
        if length != buf.getlength():
            raise oefmt(space.w_TypeError,
                        "memoryview: product(shape) * itemsize != buffer size")

        strides = self._strides_from_shape(shape, itemsize)
        return BufferViewND(buf, ndim, shape, strides)

    @staticmethod
    def _strides_from_shape(shape, itemsize):
        ndim = len(shape)
        if ndim == 0:
            return []
        s = [0] * ndim
        s[ndim - 1] = itemsize
        i = ndim - 2
        while i >= 0:
            s[i] = s[i+1] * shape[i+1]
            i -= 1
        return s

    def descr_hex(self, space):
        from pypy.objspace.std.bytearrayobject import _array_to_hexstring
        self._check_released(space)
        return _array_to_hexstring(space, self.buf.as_binary(), 0, 1, self.getlength())

def is_byte_format(char):
    return char == 'b' or char == 'B' or char == 'c'

def memory_view_c_contiguous(space, flags):
    return flags & (MEMORYVIEW_SCALAR|MEMORYVIEW_C)

W_MemoryView.typedef = TypeDef(
    "memoryview", None, None, "read-write", variable_sized=True,
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
    nbytes        = GetSetProperty(W_MemoryView.w_get_nbytes),
    readonly    = GetSetProperty(W_MemoryView.w_is_readonly),
    shape       = GetSetProperty(W_MemoryView.w_get_shape),
    strides     = GetSetProperty(W_MemoryView.w_get_strides),
    suboffsets  = GetSetProperty(W_MemoryView.w_get_suboffsets),
    _pypy_raw_address = interp2app(W_MemoryView.descr_pypy_raw_address),
    )
W_MemoryView.typedef.acceptable_as_base_class = False

def _IsFortranContiguous(ndim, shape, strides, itemsize):
    if ndim == 0:
        return 1
    if not strides:
        return ndim == 1
    sd = itemsize
    if ndim == 1:
        return shape[0] == 1 or sd == strides[0]
    for i in range(ndim):
        dim = shape[i]
        if dim == 0:
            return 1
        if strides[i] != sd:
            return 0
        sd *= dim
    return 1

def _IsCContiguous(ndim, shape, strides, itemsize):
    if ndim == 0:
        return 1
    if not strides:
        return ndim == 1
    sd = itemsize
    if ndim == 1:
        return shape[0] == 1 or sd == strides[0]
    for i in range(ndim - 1, -1, -1):
        dim = shape[i]
        if dim == 0:
            return 1
        if strides[i] != sd:
            return 0
        sd *= dim
    return 1

def PyBuffer_isContiguous(suboffsets, ndim, shape, strides, itemsize, fort):
    if suboffsets:
        return 0
    if (fort == 'C'):
        return _IsCContiguous(ndim, shape, strides, itemsize)
    elif (fort == 'F'):
        return _IsFortranContiguous(ndim, shape, strides, itemsize)
    elif (fort == 'A'):
        return (_IsCContiguous(ndim, shape, strides, itemsize) or \
                _IsFortranContiguous(ndim, shape, strides, itemsize))
    return 0

class BufferSlice(PyBuffer):
    _immutable_ = True
    _attrs_ = ['buf', 'readonly', 'shape', 'strides', 'start', 'step']
    def __init__(self, buf, start, step, length):
        self.buf = buf
        self.readonly = self.buf.readonly
        self.strides = buf.getstrides()[:]
        itemsize = buf.getitemsize()
        self.start = start
        self.step = step
        self.strides[0] *= step
        self.shape = buf.getshape()[:]
        self.shape[0] = length

    def getlength(self):
        return self.shape[0] * self.getitemsize()

    def getbytes(self, start, size):
        offset = self.start * self.buf.getstrides()[0]
        return self.buf.getbytes(offset + start, size)

    def setbytes(self, start, string):
        if len(string) == 0:
            return        # otherwise, adding self.offset might make 'start'
                          # out of bounds
        offset = self.start * self.buf.getstrides()[0]
        self.buf.setbytes(offset + start, string)

    def get_raw_address(self):
        from rpython.rtyper.lltypesystem import rffi
        offset = self.start * self.buf.getstrides()[0]
        return rffi.ptradd(self.buf.get_raw_address(), offset)

    def getformat(self):
        return self.buf.getformat()

    def getitemsize(self):
        return self.buf.getitemsize()

    def getndim(self):
        return self.buf.getndim()

    def getshape(self):
        return self.shape

    def getstrides(self):
        return self.strides

    def parent_index(self, idx):
        return self.start + self.step * idx

    def w_getitem(self, space, idx):
        return self.buf.w_getitem(space, self.parent_index(idx))

    def setitem_w(self, space, idx, w_obj):
        return self.buf.setitem_w(space, self.parent_index(idx), w_obj)


class BufferViewBase(PyBuffer):
    _immutable_ = True
    _attrs_ = ['readonly', 'parent']

    def getlength(self):
        return self.parent.getlength()

    def as_str(self):
        return self.parent.as_str()

    def as_str_and_offset_maybe(self):
        return self.parent.as_str_and_offset_maybe()

    def getbytes(self, start, size):
        return self.parent.getbytes(start, size)

    def setbytes(self, start, string):
        self.parent.setbytes(start, string)

    def get_raw_address(self):
        return self.parent.get_raw_address()

    def as_binary(self):
        return self.parent.as_binary()

    def as_binary_rw(self):
        return self.parent.as_binary_rw()

class BufferView1D(BufferViewBase):
    _immutable_ = True
    _attrs_ = ['readonly', 'parent', 'format', 'itemsize']

    def __init__(self, parent, format, itemsize):
        self.parent = parent
        self.readonly = parent.readonly
        self.format = format
        self.itemsize = itemsize

    def getformat(self):
        return self.format

    def getitemsize(self):
        return self.itemsize

    def getndim(self):
        return 1

    def getshape(self):
        return [self.getlength() // self.itemsize]

    def getstrides(self):
        return [self.itemsize]

class BufferViewND(BufferViewBase):
    _immutable_ = True
    _attrs_ = ['readonly', 'parent', 'ndim', 'shape', 'strides']

    def __init__(self, parent, ndim, shape, strides):
        assert parent.getndim() == 1
        assert len(shape) == len(strides) == ndim
        self.parent = parent
        self.readonly = parent.readonly
        self.ndim = ndim
        self.shape = shape
        self.strides = strides

    def getformat(self):
        return self.parent.getformat()

    def getitemsize(self):
        return self.parent.getitemsize()

    def getndim(self):
        return self.ndim

    def getshape(self):
        return self.shape

    def getstrides(self):
        return self.strides
