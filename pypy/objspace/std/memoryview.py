"""
Implementation of the 'buffer' and 'memoryview' types.
"""
import operator

from pypy.interpreter import buffer
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from rpython.rlib.objectmodel import compute_hash
from rpython.rlib.rstring import StringBuilder


def _buffer_setitem(space, buf, w_index, newstring):
    start, stop, step, size = space.decode_index4(w_index, buf.getlength())
    if step == 0:  # index only
        if len(newstring) != 1:
            msg = 'buffer[index]=x: x must be a single character'
            raise OperationError(space.w_TypeError, space.wrap(msg))
        char = newstring[0]   # annotator hint
        buf.setitem(start, char)
    elif step == 1:
        if len(newstring) != size:
            msg = "right operand length must match slice length"
            raise OperationError(space.w_ValueError, space.wrap(msg))
        buf.setslice(start, newstring)
    else:
        raise OperationError(space.w_ValueError,
                             space.wrap("buffer object does not support"
                                        " slicing with a step"))


class W_MemoryView(W_Root):
    """Implement the built-in 'memoryview' type as a wrapper around
    an interp-level buffer.
    """

    def __init__(self, buf):
        assert isinstance(buf, buffer.Buffer)
        self.buf = buf

    def buffer_w(self, space):
        """
        Note that memoryview() is very inconsistent in CPython: it does not
        support the buffer interface but does support the new buffer
        interface: as a result, it is possible to pass memoryview to
        e.g. socket.send() but not to file.write().  For simplicity and
        consistency, in PyPy memoryview DOES support buffer(), which means
        that it is accepted in more places than CPython.
        """
        self._check_released(space)
        return self.buf

    @staticmethod
    def descr_new_memoryview(space, w_subtype, w_object):
        return W_MemoryView(space.buffer_w(w_object))

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
                buf = space.buffer_w(w_other)
            except OperationError, e:
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

    def descr_tobytes(self, space):
        self._check_released(space)
        return space.wrapbytes(self.as_str())

    def descr_tolist(self, space):
        self._check_released(space)
        buf = self.buf
        result = []
        for i in range(buf.getlength()):
            result.append(space.wrap(ord(buf.getitem(i))))
        return space.newlist(result)

    def descr_getitem(self, space, w_index):
        self._check_released(space)
        start, stop, step = space.decode_index(w_index, self.getlength())
        if step == 0:  # index only
            return space.wrapbytes(self.buf.getitem(start))
        elif step == 1:
            res = self.getslice(start, stop)
            return space.wrap(res)
        else:
            raise OperationError(space.w_ValueError,
                space.wrap("memoryview object does not support"
                           " slicing with a step"))

    @unwrap_spec(newstring='bufferstr')
    def descr_setitem(self, space, w_index, newstring):
        self._check_released(space)
        if not isinstance(self.buf, buffer.RWBuffer):
            raise OperationError(space.w_TypeError,
                                 space.wrap("cannot modify read-only memory"))
        _buffer_setitem(space, self.buf, w_index, newstring)

    def descr_len(self, space):
        self._check_released(space)
        return space.wrap(self.buf.getlength())

    def w_get_format(self, space):
        self._check_released(space)
        return space.wrap("B")

    def w_get_itemsize(self, space):
        self._check_released(space)
        return space.wrap(1)

    def w_get_ndim(self, space):
        self._check_released(space)
        return space.wrap(1)

    def w_is_readonly(self, space):
        self._check_released(space)
        return space.wrap(not isinstance(self.buf, buffer.RWBuffer))

    def w_get_shape(self, space):
        self._check_released(space)
        return space.newtuple([space.wrap(self.getlength())])

    def w_get_strides(self, space):
        self._check_released(space)
        return space.newtuple([space.wrap(1)])

    def w_get_suboffsets(self, space):
        self._check_released(space)
        # I've never seen anyone filling this field
        return space.w_None

    def descr_repr(self, space):
        if self.buf is None:
            return self.getrepr(space, u'released memory')
        else:
            return self.getrepr(space, u'memory')

    def descr_release(self, space):
        self.buf = None

    def _check_released(self, space):
        if self.buf is None:
            raise OperationError(space.w_ValueError, space.wrap(
                    "operation forbidden on released memoryview object"))

    def descr_enter(self, space):
        self._check_released(space)
        return self

    def descr_exit(self, space, __args__):
        self.buf = None
        return space.w_None


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
    __enter__   = interp2app(W_MemoryView.descr_enter),
    __exit__    = interp2app(W_MemoryView.descr_exit),
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
    )
W_MemoryView.typedef.acceptable_as_base_class = False
