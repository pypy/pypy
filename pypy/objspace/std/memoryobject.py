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
from pypy.objspace.std.bytesobject import getbytevalue
from pypy.module.struct.formatiterator import UnpackFormatIterator, PackFormatIterator


class W_MemoryView(W_Root):
    """Implement the built-in 'memoryview' type as a wrapper around
    an interp-level buffer.
    """
    _immutable_fields_ = ['format', 'itemsize']

    def __init__(self, buf, format='B', itemsize=1):
        assert isinstance(buf, Buffer)
        self.buf = buf
        self._hash = -1
        self.format = format
        self.itemsize = itemsize

    def buffer_w_ex(self, space, flags):
        self._check_released(space)
        space.check_buf_flags(flags, self.buf.readonly)
        return self.buf, self.format, self.itemsize

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
        buf = self.buf
        return buf.as_str()

    def getlength(self):
        return self.buf.getlength() // self.itemsize

    def descr_tobytes(self, space):
        self._check_released(space)
        return space.newbytes(self.as_str())

    def descr_tolist(self, space):
        self._check_released(space)
        # TODO: this probably isn't very fast
        fmtiter = UnpackFormatIterator(space, self.buf)
        fmtiter.interpret(self.format * self.getlength())
        return space.newlist(fmtiter.result_w)

    def descr_getitem(self, space, w_index):
        self._check_released(space)
        start, stop, step, size = space.decode_index4(w_index, self.getlength())
        # ^^^ for a non-slice index, this returns (index, 0, 0, 1)
        itemsize = self.itemsize
        if step == 0:  # index only
            if itemsize == 1:
                ch = self.buf.getitem(start)
                return space.newint(ord(ch))
            else:
                # TODO: this probably isn't very fast
                buf = SubBuffer(self.buf, start * itemsize, itemsize)
                fmtiter = UnpackFormatIterator(space, buf)
                fmtiter.interpret(self.format)
                return fmtiter.result_w[0]
        elif step == 1:
            buf = SubBuffer(self.buf, start * itemsize, size * itemsize)
            return W_MemoryView(buf, self.format, itemsize)
        else:
            raise oefmt(space.w_NotImplementedError,
                        "XXX extended slicing")

    def descr_setitem(self, space, w_index, w_obj):
        self._check_released(space)
        if self.buf.readonly:
            raise oefmt(space.w_TypeError, "cannot modify read-only memory")
        if space.isinstance_w(w_index, space.w_tuple):
            raise oefmt(space.w_NotImplementedError, "XXX tuple setitem")
        start, stop, step, size = space.decode_index4(w_index, self.getlength())
        itemsize = self.itemsize
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
                self.buf.setslice(start * itemsize, fmtiter.result.build())
        elif step == 1:
            value = space.buffer_w(w_obj, space.BUF_CONTIG_RO)
            if value.getlength() != size * self.itemsize:
                raise oefmt(space.w_ValueError,
                            "cannot modify size of memoryview object")
            self.buf.setslice(start * itemsize, value.as_str())
        else:
            raise oefmt(space.w_NotImplementedError,
                        "XXX extended slicing")

    def descr_len(self, space):
        self._check_released(space)
        return space.wrap(self.getlength())

    def w_get_format(self, space):
        self._check_released(space)
        return space.wrap(self.format)

    def w_get_itemsize(self, space):
        self._check_released(space)
        return space.newint(self.itemsize)

    def w_get_ndim(self, space):
        self._check_released(space)
        return space.wrap(self.buf.getndim())

    def w_is_readonly(self, space):
        self._check_released(space)
        return space.newbool(bool(self.buf.readonly))

    def w_get_shape(self, space):
        self._check_released(space)
        return space.newtuple([space.newint(self.getlength())])

    def w_get_strides(self, space):
        self._check_released(space)
        return space.newtuple([space.newint(self.itemsize)])

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

    def descr_cast(self, space, w_format, w_shape=None):
        self._check_released(space)
        if not space.is_none(w_shape):
            raise oefmt(space.w_NotImplementedError,
                        "XXX cast() with a shape")
        fmt = space.str_w(w_format)
        newitemsize = self.get_native_fmtchar(fmt)
        return W_MemoryView(self.buf, fmt, newitemsize)

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
