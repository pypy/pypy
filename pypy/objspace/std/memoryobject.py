"""
Implementation of the 'buffer' and 'memoryview' types.
"""
import operator

from rpython.rlib.buffer import SubBuffer
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import BufferView
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty

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

    def __init__(self, view):
        assert isinstance(view, BufferView)
        self.view = view
        self._hash = -1
        self.flags = 0
        self._init_flags()

    def getndim(self):
        return self.view.getndim()

    def getshape(self):
        return self.view.getshape()

    def getstrides(self):
        return self.view.getstrides()

    def getitemsize(self):
        return self.view.getitemsize()

    def getformat(self):
        return self.view.getformat()

    def buffer_w(self, space, flags):
        self._check_released(space)
        space.check_buf_flags(flags, self.view.readonly)
        return self.view

    @staticmethod
    def descr_new_memoryview(space, w_subtype, w_object):
        if isinstance(w_object, W_MemoryView):
            w_object._check_released(space)
            return W_MemoryView.copy(w_object)
        view = space.buffer_w(w_object, space.BUF_FULL_RO)
        return view.wrap(space)

    def _make_descr__cmp(name):
        def descr__cmp(self, space, w_other):
            if isinstance(w_other, W_MemoryView):
                # xxx not the most efficient implementation
                str1 = self.view.as_str()
                str2 = w_other.view.as_str()
                return space.newbool(getattr(operator, name)(str1, str2))

            try:
                view = space.buffer_w(w_other, space.BUF_CONTIG_RO)
            except OperationError as e:
                if not e.match(space, space.w_TypeError):
                    raise
                return space.w_NotImplemented
            else:
                str1 = self.view.as_str()
                str2 = view.as_str()
                return space.newbool(getattr(operator, name)(str1, str2))
        descr__cmp.func_name = name
        return descr__cmp

    descr_eq = _make_descr__cmp('eq')
    descr_ne = _make_descr__cmp('ne')
    descr_lt = _make_descr__cmp('lt')
    descr_le = _make_descr__cmp('le')
    descr_gt = _make_descr__cmp('gt')
    descr_ge = _make_descr__cmp('ge')

    def as_str(self):
        return self.buf.as_str()

    def getlength(self):
        return self.view.getlength()

    def descr_tobytes(self, space):
        self._check_released(space)
        return space.newbytes(self.view.as_str())

    def descr_tolist(self, space):
        self._check_released(space)
        return self.view.w_tolist(space)

    def _decode_index(self, space, w_index, is_slice):
        shape = self.getshape()
        if len(shape) == 0:
            count = 1
        else:
            count = shape[0]
        return space.decode_index4(w_index, count)

    def descr_getitem(self, space, w_index):
        is_slice = space.isinstance_w(w_index, space.w_slice)
        start, stop, step, slicelength = self._decode_index(space, w_index, is_slice)
        # ^^^ for a non-slice index, this returns (index, 0, 0, 1)
        if step not in (0, 1):
            raise oefmt(space.w_NotImplementedError, "")
        if step == 0:  # index only
            dim = self.getndim()
            if dim == 0:
                raise oefmt(space.w_TypeError, "invalid indexing of 0-dim memory")
            elif dim == 1:
                return self.view.w_getitem(space, start)
            else:
                raise oefmt(space.w_NotImplementedError, "multi-dimensional sub-views are not implemented")
        elif is_slice:
            return self.view.new_slice(start, step, slicelength).wrap(space)
        # multi index is handled at the top of this function
        else:
            raise TypeError("memoryview: invalid slice key")

    @staticmethod
    def copy(w_view):
        # TODO suboffsets
        view = w_view.view
        return W_MemoryView(view)

    def descr_setitem(self, space, w_index, w_obj):
        self._check_released(space)
        if self.view.readonly:
            raise oefmt(space.w_TypeError, "cannot modify read-only memory")
        start, stop, step, size = space.decode_index4(w_index, self.getlength())
        if step not in (0, 1):
            raise oefmt(space.w_NotImplementedError, "")
        is_slice = space.isinstance_w(w_index, space.w_slice)
        start, stop, step, slicelength = self._decode_index(space, w_index, is_slice)
        itemsize = self.getitemsize()
        value = space.buffer_w(w_obj, space.BUF_CONTIG_RO)
        if value.getlength() != slicelength * itemsize:
            raise oefmt(space.w_ValueError,
                        "cannot modify size of memoryview object")
        self.view.setbytes(start * itemsize, value.as_str())

    def descr_len(self, space):
        self._check_released(space)
        dim = self.getndim()
        if dim == 0:
            return space.newint(1)
        shape = self.getshape()
        return space.newint(shape[0])

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
        return space.newbool(bool(self.view.readonly))

    def w_get_shape(self, space):
        self._check_released(space)
        if self.view.getndim() == 0:
            return space.w_None
        return space.newtuple([space.newint(x) for x in self.getshape()])

    def w_get_strides(self, space):
        self._check_released(space)
        if self.view.getndim() == 0:
            return space.w_None
        return space.newtuple([space.newint(x) for x in self.getstrides()])

    def w_get_suboffsets(self, space):
        self._check_released(space)
        # I've never seen anyone filling this field
        return space.w_None

    def _check_released(self, space):
        if self.view is None:
            raise oefmt(space.w_ValueError,
                        "operation forbidden on released memoryview object")

    def descr_pypy_raw_address(self, space):
        from rpython.rtyper.lltypesystem import lltype, rffi
        try:
            ptr = self.view.get_raw_address()
        except ValueError:
            # report the error using the RPython-level internal repr of
            # self.view
            msg = ("cannot find the underlying address of buffer that "
                   "is internally %r" % (self.view,))
            raise OperationError(space.w_ValueError, space.newtext(msg))
        return space.newint(rffi.cast(lltype.Signed, ptr))

    def _init_flags(self):
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

W_MemoryView.typedef = TypeDef(
    "memoryview",
    __doc__ = """\
Create a new memoryview object which references the given object.
""",
    __new__     = interp2app(W_MemoryView.descr_new_memoryview),
    __eq__      = interp2app(W_MemoryView.descr_eq),
    __ge__      = interp2app(W_MemoryView.descr_ge),
    __getitem__ = interp2app(W_MemoryView.descr_getitem),
    __gt__      = interp2app(W_MemoryView.descr_gt),
    __le__      = interp2app(W_MemoryView.descr_le),
    __len__     = interp2app(W_MemoryView.descr_len),
    __lt__      = interp2app(W_MemoryView.descr_lt),
    __ne__      = interp2app(W_MemoryView.descr_ne),
    __setitem__ = interp2app(W_MemoryView.descr_setitem),
    tobytes     = interp2app(W_MemoryView.descr_tobytes),
    tolist      = interp2app(W_MemoryView.descr_tolist),
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
        return (_IsCContiguous(ndim, shape, strides, itemsize) or
                _IsFortranContiguous(ndim, shape, strides, itemsize))
    return 0
