"""
Implementation of the 'buffer' and 'memoryview' types.
"""
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import gateway, buffer
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.error import OperationError
import operator

W_Buffer = buffer.Buffer      # actually implemented in pypy.interpreter.buffer


class W_MemoryView(Wrappable):
    """Implement the built-in 'memoryview' type as a thin wrapper around
    an interp-level buffer.
    """

    def __init__(self, buf):
        assert isinstance(buf, buffer.Buffer)
        self.buf = buf

    def _make_descr__cmp(name):
        def descr__cmp(self, space, w_other):
            other = space.interpclass_w(w_other)
            if isinstance(other, W_MemoryView):
                # xxx not the most efficient implementation
                str1 = self.as_str()
                str2 = other.as_str()
                return space.wrap(getattr(operator, name)(str1, str2))

            try:
                w_buf = space.buffer(w_other)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                return space.w_NotImplemented
            else:
                str1 = self.as_str()
                str2 = space.buffer_w(w_buf).as_str()
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

    def getslice(self, start, stop):
        if start < 0:
            start = 0
        size = stop - start
        if size < 0:
            size = 0
        buf = self.buf
        if isinstance(buf, buffer.RWBuffer):
            buf = buffer.RWSubBuffer(buf, start, size)
        else:
            buf = buffer.SubBuffer(buf, start, size)
        return W_MemoryView(buf)

    def descr_buffer(self, space):
        return space.wrap(self.buf)

    def descr_tobytes(self, space):
        return space.wrap(self.as_str())

    def descr_tolist(self, space):
        buf = self.buf
        result = []
        for i in range(buf.getlength()):
            result.append(space.wrap(ord(buf.getitem(i))))
        return space.newlist(result)

    def descr_getitem(self, space, w_index):
        start, stop, step = space.decode_index(w_index, self.getlength())
        if step == 0:  # index only
            return space.wrap(self.buf.getitem(start))
        elif step == 1:
            res = self.getslice(start, stop)
            return space.wrap(res)
        else:
            raise OperationError(space.w_ValueError,
                space.wrap("memoryview object does not support"
                           " slicing with a step"))

    @unwrap_spec(newstring='bufferstr')
    def descr_setitem(self, space, w_index, newstring):
        buf = self.buf
        if isinstance(buf, buffer.RWBuffer):
            buf.descr_setitem(space, w_index, newstring)
        else:
            raise OperationError(space.w_TypeError,
                                 space.wrap("cannot modify read-only memory"))

    def descr_len(self, space):
        return self.buf.descr_len(space)

    def w_get_format(self, space):
        return space.wrap("B")
    def w_get_itemsize(self, space):
        return space.wrap(1)
    def w_get_ndim(self, space):
        return space.wrap(1)
    def w_is_readonly(self, space):
        return space.wrap(not isinstance(self.buf, buffer.RWBuffer))
    def w_get_shape(self, space):
        return space.newtuple([space.wrap(self.getlength())])
    def w_get_strides(self, space):
        return space.newtuple([space.wrap(1)])
    def w_get_suboffsets(self, space):
        # I've never seen anyone filling this field
        return space.w_None


def descr_new(space, w_subtype, w_object):
    memoryview = W_MemoryView(space.buffer(w_object))
    return space.wrap(memoryview)

W_MemoryView.typedef = TypeDef(
    "memoryview",
    __doc__ = """\
Create a new memoryview object which references the given object.
""",
    __new__ = interp2app(descr_new),
    __buffer__  = interp2app(W_MemoryView.descr_buffer),
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
    )
W_MemoryView.typedef.acceptable_as_base_class = False
