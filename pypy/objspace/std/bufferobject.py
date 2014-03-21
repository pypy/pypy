"""
Implementation of the 'buffer' and 'memoryview' types.
"""
import operator

from pypy.interpreter import buffer
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from rpython.rlib.objectmodel import compute_hash
from rpython.rlib.rstring import StringBuilder
from pypy.objspace.std.memoryobject import _buffer_setitem


class W_Buffer(W_Root):
    """Implement the built-in 'buffer' type as a wrapper around
    an interp-level buffer.
    """

    def __init__(self, buf):
        assert isinstance(buf, buffer.Buffer)
        self.buf = buf

    def buffer_w(self, space, flags):
        return self.buf

    def readbuf_w(self, space):
        return self.buf

    def writebuf_w(self, space):
        return self.buf

    def charbuf_w(self, space):
        return self.buf.as_str()

    @staticmethod
    @unwrap_spec(offset=int, size=int)
    def descr_new_buffer(space, w_subtype, w_object, offset=0, size=-1):
        if space.isinstance_w(w_object, space.w_unicode):
            # unicode objects support the old buffer interface
            # but not the new buffer interface (change in python 2.7)
            from rpython.rlib.rstruct.unichar import pack_unichar, UNICODE_SIZE
            unistr = space.unicode_w(w_object)
            builder = StringBuilder(len(unistr) * UNICODE_SIZE)
            for unich in unistr:
                pack_unichar(unich, builder)
            from pypy.interpreter.buffer import StringBuffer
            buf = StringBuffer(builder.build())
        else:
            buf = space.readbuf_w(w_object)

        if offset == 0 and size == -1:
            return W_Buffer(buf)
        # handle buffer slices
        if offset < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("offset must be zero or positive"))
        if size < -1:
            raise OperationError(space.w_ValueError,
                                 space.wrap("size must be zero or positive"))
        if isinstance(buf, buffer.RWBuffer):
            buf = buffer.RWSubBuffer(buf, offset, size)
        else:
            buf = buffer.SubBuffer(buf, offset, size)
        return W_Buffer(buf)

    def descr_len(self, space):
        return space.wrap(self.buf.getlength())

    def descr_getitem(self, space, w_index):
        start, stop, step, size = space.decode_index4(w_index, self.buf.getlength())
        if step == 0:  # index only
            return space.wrap(self.buf.getitem(start))
        res = self.buf.getslice(start, stop, step, size)
        return space.wrap(res)

    @unwrap_spec(newstring='bufferstr')
    def descr_setitem(self, space, w_index, newstring):
        if not isinstance(self.buf, buffer.RWBuffer):
            raise OperationError(space.w_TypeError,
                                 space.wrap("buffer is read-only"))
        _buffer_setitem(space, self.buf, w_index, newstring)

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
        if isinstance(self.buf, buffer.RWBuffer):
            info = 'read-write buffer'
        else:
            info = 'read-only buffer'
        addrstring = self.getaddrstring(space)

        return space.wrap("<%s for 0x%s, size %d>" %
                          (info, addrstring, self.buf.getlength()))

W_Buffer.typedef = TypeDef(
    "buffer",
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
)
W_Buffer.typedef.acceptable_as_base_class = False
