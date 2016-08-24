"""
Implementation of the 'buffer' and 'memoryview' types.
"""
import operator

from rpython.rlib.buffer import Buffer, SubBuffer
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty


class W_MemoryView(W_Root):
    """Implement the built-in 'memoryview' type as a wrapper around
    an interp-level buffer.
    """

    def __init__(self, buf):
        assert isinstance(buf, Buffer)
        self.buf = buf

    def buffer_w(self, space, flags):
        space.check_buf_flags(flags, self.buf.readonly)
        return self.buf

    @staticmethod
    def descr_new_memoryview(space, w_subtype, w_object):
        return W_MemoryView(space.buffer_w(w_object, space.BUF_FULL_RO))

    def _make_descr__cmp(name):
        def descr__cmp(self, space, w_other):
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
    descr_lt = _make_descr__cmp('lt')
    descr_le = _make_descr__cmp('le')
    descr_gt = _make_descr__cmp('gt')
    descr_ge = _make_descr__cmp('ge')

    def as_str(self):
        return self.buf.as_str()

    def getlength(self):
        return self.buf.getlength()

    def descr_tobytes(self, space):
        return space.wrap(self.as_str())

    def descr_tolist(self, space):
        buf = self.buf
        result = []
        for i in range(buf.getlength()):
            result.append(space.wrap(ord(buf.getitem(i))))
        return space.newlist(result)

    def descr_getitem(self, space, w_index):
        start, stop, step, size = space.decode_index4(w_index, self.getlength())
        itemsize = self.buf.getitemsize()
        if itemsize > 1:
            start *= itemsize
            size *= itemsize
            stop  = start + size
            if step == 0:
                step = 1
            if stop > self.getlength():
                raise oefmt(space.w_IndexError, 'index out of range')
        if step not in (0, 1):
            raise oefmt(space.w_NotImplementedError, "")
        if step == 0:  # index only
            return space.wrap(self.buf.getitem(start))
        else:
            buf = SubBuffer(self.buf, start, size)
            return W_MemoryView(buf)

    def descr_setitem(self, space, w_index, w_obj):
        if self.buf.readonly:
            raise oefmt(space.w_TypeError, "cannot modify read-only memory")
        start, stop, step, size = space.decode_index4(w_index, self.getlength())
        itemsize = self.buf.getitemsize()
        if itemsize > 1:
            start *= itemsize
            size *= itemsize
            stop  = start + size
            if step == 0:
                step = 1
            if stop > self.getlength():
                raise oefmt(space.w_IndexError, 'index out of range')
        if step not in (0, 1):
            raise oefmt(space.w_NotImplementedError, "")
        value = space.buffer_w(w_obj, space.BUF_CONTIG_RO)
        if value.getlength() != size:
            raise oefmt(space.w_ValueError,
                        "cannot modify size of memoryview object")
        if step == 0:  # index only
            self.buf.setitem(start, value.getitem(0))
        elif step == 1:
            self.buf.setslice(start, value.as_str())

    def descr_len(self, space):
        return space.wrap(self.buf.getlength())

    def w_get_format(self, space):
        return space.wrap(self.buf.getformat())

    def w_get_itemsize(self, space):
        return space.wrap(self.buf.getitemsize())

    def w_get_ndim(self, space):
        return space.wrap(self.buf.getndim())

    def w_is_readonly(self, space):
        return space.newbool(bool(self.buf.readonly))

    def w_get_shape(self, space):
        return space.newtuple([space.wrap(x) for x in self.buf.getshape()])

    def w_get_strides(self, space):
        return space.newtuple([space.wrap(x) for x in self.buf.getstrides()])

    def w_get_suboffsets(self, space):
        # I've never seen anyone filling this field
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
