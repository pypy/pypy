"""Implementation of the 'buffer' type"""
import operator

from rpython.rlib.buffer import Buffer, SubBuffer
from rpython.rlib.objectmodel import compute_hash

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef


class W_Buffer(W_Root):
    """The 'buffer' type: a wrapper around an interp-level buffer"""

    def __init__(self, buf):
        assert isinstance(buf, Buffer)
        self.buf = buf

    def buffer_w(self, space, flags):
        space.check_buf_flags(flags, self.buf.readonly)
        return self.buf

    def readbuf_w(self, space):
        return self.buf

    def writebuf_w(self, space):
        if self.buf.readonly:
            raise oefmt(space.w_TypeError, "buffer is read-only")
        return self.buf

    def charbuf_w(self, space):
        return self.buf.as_str()

    def descr_getbuffer(self, space, w_flags):
        space.check_buf_flags(space.int_w(w_flags), self.buf.readonly)
        return self

    @staticmethod
    @unwrap_spec(offset=int, size=int)
    def descr_new_buffer(space, w_subtype, w_object, offset=0, size=-1):
        buf = space.readbuf_w(w_object)
        if offset == 0 and size == -1:
            return W_Buffer(buf)
        # handle buffer slices
        if offset < 0:
            raise oefmt(space.w_ValueError, "offset must be zero or positive")
        if size < -1:
            raise oefmt(space.w_ValueError, "size must be zero or positive")
        buf = SubBuffer(buf, offset, size)
        return W_Buffer(buf)

    def descr_len(self, space):
        return space.wrap(self.buf.getlength())

    def descr_getitem(self, space, w_index):
        start, stop, step, size = space.decode_index4(w_index,
                                                      self.buf.getlength())
        if step == 0:  # index only
            return space.wrap(self.buf.getitem(start))
        res = self.buf.getslice(start, stop, step, size)
        return space.wrap(res)

    def descr_setitem(self, space, w_index, w_obj):
        if self.buf.readonly:
            raise oefmt(space.w_TypeError, "buffer is read-only")
        start, stop, step, size = space.decode_index4(w_index,
                                                      self.buf.getlength())
        value = space.readbuf_w(w_obj)
        if step == 0:  # index only
            if value.getlength() != 1:
                raise oefmt(space.w_TypeError,
                            "right operand must be a single byte")
            self.buf.setitem(start, value.getitem(0))
        else:
            if value.getlength() != size:
                raise oefmt(space.w_TypeError,
                            "right operand length must match slice length")
            if step == 1:
                self.buf.setslice(start, value.as_str())
            else:
                for i in range(size):
                    self.buf.setitem(start + i * step, value.getitem(i))

    def descr_str(self, space):
        return space.wrap(self.buf.as_str())

    @unwrap_spec(other='bufferstr')
    def descr_add(self, space, other):
        return space.wrap(self.buf.as_str() + other)

    def _make_descr__cmp(name):
        def descr__cmp(self, space, w_other):
            if not isinstance(w_other, W_Buffer):
                return space.w_NotImplemented
            # xxx not the most efficient implementation
            str1 = self.buf.as_str()
            str2 = w_other.buf.as_str()
            return space.wrap(getattr(operator, name)(str1, str2))
        descr__cmp.func_name = name
        return descr__cmp

    descr_eq = _make_descr__cmp('eq')
    descr_ne = _make_descr__cmp('ne')
    descr_lt = _make_descr__cmp('lt')
    descr_le = _make_descr__cmp('le')
    descr_gt = _make_descr__cmp('gt')
    descr_ge = _make_descr__cmp('ge')

    def descr_hash(self, space):
        return space.wrap(compute_hash(self.buf.as_str()))

    def descr_mul(self, space, w_times):
        # xxx not the most efficient implementation
        w_string = space.wrap(self.buf.as_str())
        # use the __mul__ method instead of space.mul() so that we
        # return NotImplemented instead of raising a TypeError
        return space.call_method(w_string, '__mul__', w_times)

    def descr_repr(self, space):
        if self.buf.readonly:
            info = 'read-only buffer'
        else:
            info = 'read-write buffer'
        addrstring = self.getaddrstring(space)

        return space.wrap("<%s for 0x%s, size %d>" %
                          (info, addrstring, self.buf.getlength()))

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

W_Buffer.typedef = TypeDef(
    "buffer", None, None, "read-write",
    __doc__ = """\
buffer(object [, offset[, size]])

Create a new buffer object which references the given object.
The buffer will reference a slice of the target object from the
start of the object (or at the specified offset). The slice will
extend to the end of the target object (or with the specified size).
""",
    __new__ = interp2app(W_Buffer.descr_new_buffer),
    __len__ = interp2app(W_Buffer.descr_len),
    __getitem__ = interp2app(W_Buffer.descr_getitem),
    __setitem__ = interp2app(W_Buffer.descr_setitem),
    __str__ = interp2app(W_Buffer.descr_str),
    __add__ = interp2app(W_Buffer.descr_add),
    __eq__ = interp2app(W_Buffer.descr_eq),
    __ne__ = interp2app(W_Buffer.descr_ne),
    __lt__ = interp2app(W_Buffer.descr_lt),
    __le__ = interp2app(W_Buffer.descr_le),
    __gt__ = interp2app(W_Buffer.descr_gt),
    __ge__ = interp2app(W_Buffer.descr_ge),
    __hash__ = interp2app(W_Buffer.descr_hash),
    __mul__ = interp2app(W_Buffer.descr_mul),
    __rmul__ = interp2app(W_Buffer.descr_mul),
    __repr__ = interp2app(W_Buffer.descr_repr),
    __buffer__ = interp2app(W_Buffer.descr_getbuffer),
    _pypy_raw_address = interp2app(W_Buffer.descr_pypy_raw_address),
)
W_Buffer.typedef.acceptable_as_base_class = False
