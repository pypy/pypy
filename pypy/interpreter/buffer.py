"""
Buffer protocol support.
"""

# The implementation of the buffer protocol.  The basic idea is that we
# can ask any app-level object for a 'buffer' view on it, by calling its
# __buffer__() special method.  It should return a wrapped instance of a
# subclass of the Buffer class defined below.  Note that __buffer__() is
# a PyPy-only extension to the Python language, made necessary by the
# fact that it's not natural in PyPy to hack an interp-level-only
# interface.

# In normal usage, the convenience method space.buffer_w() should be
# used to get directly a Buffer instance.  Doing so also gives you for
# free the typecheck that __buffer__() really returned a wrapped Buffer.

import operator
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.rlib.objectmodel import compute_hash


class Buffer(Wrappable):
    """Abstract base class for memory views."""

    __slots__ = ()     # no extra slot here

    def getlength(self):
        raise NotImplementedError

    def as_str(self):
        "Returns an interp-level string with the whole content of the buffer."
        # May be overridden.
        return self.getslice(0, self.getlength(), 1, self.getlength())

    def getitem(self, index):
        "Returns the index'th character in the buffer."
        raise NotImplementedError   # Must be overriden.  No bounds checks.

    def getslice(self, start, stop, step, size):
        # May be overridden.  No bounds checks.
        return ''.join([self.getitem(i) for i in range(start, stop, step)])

    def get_raw_address(self):
        raise ValueError("no raw buffer")

    # __________ app-level support __________

    def descr_len(self, space):
        return space.wrap(self.getlength())

    def descr_getitem(self, space, w_index):
        start, stop, step, size = space.decode_index4(w_index, self.getlength())
        if step == 0:  # index only
            return space.wrap(self.getitem(start))
        res = self.getslice(start, stop, step, size)
        return space.wrap(res)

    @unwrap_spec(newstring='bufferstr')
    def descr_setitem(self, space, w_index, newstring):
        if not isinstance(self, RWBuffer):
            raise OperationError(space.w_TypeError,
                                 space.wrap("buffer is read-only"))
        start, stop, step = space.decode_index(w_index, self.getlength())
        if step == 0:  # index only
            if len(newstring) != 1:
                msg = 'buffer[index]=x: x must be a single character'
                raise OperationError(space.w_TypeError, space.wrap(msg))
            char = newstring[0]   # annotator hint
            self.setitem(start, char)
        elif step == 1:
            length = stop - start
            if length != len(newstring):
                msg = "buffer slice assignment is wrong size"
                raise OperationError(space.w_ValueError, space.wrap(msg))
            self.setslice(start, newstring)
        else:
            raise OperationError(space.w_ValueError,
                                 space.wrap("buffer object does not support"
                                            " slicing with a step"))

    def descr__buffer__(self, space):
        return space.wrap(self)

    def descr_str(self, space):
        return space.wrap(self.as_str())

    @unwrap_spec(other='bufferstr')
    def descr_add(self, space, other):
        return space.wrap(self.as_str() + other)

    def _make_descr__cmp(name):
        def descr__cmp(self, space, w_other):
            other = space.interpclass_w(w_other)
            if not isinstance(other, Buffer):
                return space.w_NotImplemented
            # xxx not the most efficient implementation
            str1 = self.as_str()
            str2 = other.as_str()
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
        return space.wrap(compute_hash(self.as_str()))

    def descr_mul(self, space, w_times):
        # xxx not the most efficient implementation
        w_string = space.wrap(self.as_str())
        # use the __mul__ method instead of space.mul() so that we
        # return NotImplemented instead of raising a TypeError
        return space.call_method(w_string, '__mul__', w_times)

    def descr_repr(self, space):
        if isinstance(self, RWBuffer):
            info = 'read-write buffer'
        else:
            info = 'read-only buffer'
        addrstring = self.getaddrstring(space)

        return space.wrap("<%s for 0x%s, size %d>" %
                          (info, addrstring, self.getlength()))


class RWBuffer(Buffer):
    """Abstract base class for read-write memory views."""

    __slots__ = ()     # no extra slot here

    def setitem(self, index, char):
        "Write a character into the buffer."
        raise NotImplementedError   # Must be overriden.  No bounds checks.

    def setslice(self, start, string):
        # May be overridden.  No bounds checks.
        for i in range(len(string)):
            self.setitem(start + i, string[i])

@unwrap_spec(offset=int, size=int)
def descr_buffer__new__(space, w_subtype, w_object, offset=0, size=-1):
    # w_subtype can only be exactly 'buffer' for now
    if not space.is_w(w_subtype, space.gettypefor(Buffer)):
        raise OperationError(space.w_TypeError,
                             space.wrap("argument 1 must be 'buffer'"))

    if space.isinstance_w(w_object, space.w_unicode):
        # unicode objects support the old buffer interface
        # but not the new buffer interface (change in python  2.7)
        from pypy.rlib.rstruct.unichar import pack_unichar
        charlist = []
        for unich in space.unicode_w(w_object):
            pack_unichar(unich, charlist)
        from pypy.interpreter.buffer import StringBuffer
        w_buffer = space.wrap(StringBuffer(''.join(charlist)))
    else:
        w_buffer = space.buffer(w_object)

    buffer = space.interp_w(Buffer, w_buffer)    # type-check
    if offset == 0 and size == -1:
        return w_buffer
    # handle buffer slices
    if offset < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("offset must be zero or positive"))
    if size < -1:
        raise OperationError(space.w_ValueError,
                             space.wrap("size must be zero or positive"))
    if isinstance(buffer, RWBuffer):
        buffer = RWSubBuffer(buffer, offset, size)
    else:
        buffer = SubBuffer(buffer, offset, size)
    return space.wrap(buffer)


Buffer.typedef = TypeDef(
    "buffer",
    __doc__ = """\
buffer(object [, offset[, size]])

Create a new buffer object which references the given object.
The buffer will reference a slice of the target object from the
start of the object (or at the specified offset). The slice will
extend to the end of the target object (or with the specified size).
""",
    __new__ = interp2app(descr_buffer__new__),
    __len__ = interp2app(Buffer.descr_len),
    __getitem__ = interp2app(Buffer.descr_getitem),
    __setitem__ = interp2app(Buffer.descr_setitem),
    __buffer__ = interp2app(Buffer.descr__buffer__),
    __str__ = interp2app(Buffer.descr_str),
    __add__ = interp2app(Buffer.descr_add),
    __eq__ = interp2app(Buffer.descr_eq),
    __ne__ = interp2app(Buffer.descr_ne),
    __lt__ = interp2app(Buffer.descr_lt),
    __le__ = interp2app(Buffer.descr_le),
    __gt__ = interp2app(Buffer.descr_gt),
    __ge__ = interp2app(Buffer.descr_ge),
    __hash__ = interp2app(Buffer.descr_hash),
    __mul__ = interp2app(Buffer.descr_mul),
    __rmul__ = interp2app(Buffer.descr_mul),
    __repr__ = interp2app(Buffer.descr_repr),
    )
Buffer.typedef.acceptable_as_base_class = False

# ____________________________________________________________

class StringBuffer(Buffer):

    def __init__(self, value):
        self.value = value

    def getlength(self):
        return len(self.value)

    def as_str(self):
        return self.value

    def getitem(self, index):
        return self.value[index]

    def getslice(self, start, stop, step, size):
        if size == 0:
            return ""
        if step == 1:
            assert 0 <= start <= stop
            return self.value[start:stop]
        return "".join([self.value[start + i*step] for i in xrange(size)])


class StringLikeBuffer(Buffer):
    """For app-level objects that already have a string-like interface
    with __len__ and a __getitem__ that returns characters or (with
    slicing) substrings."""
    # XXX this is inefficient, it should only be used temporarily

    def __init__(self, space, w_obj):
        self.space = space
        self.w_obj = w_obj

    def getlength(self):
        space = self.space
        return space.len_w(self.w_obj)

    def getitem(self, index):
        space = self.space
        s = space.str_w(space.getitem(self.w_obj, space.wrap(index)))
        if len(s) != 1:
            raise OperationError(space.w_ValueError,
                                 space.wrap("character expected, got string"))
        char = s[0]   # annotator hint
        return char

    def getslice(self, start, stop, step, size):
        space = self.space
        if step != 1:
            raise OperationError(space.w_ValueError, space.wrap(
                "buffer object does not support slicing with a step"))
        s = space.str_w(space.getslice(self.w_obj, space.wrap(start),
                                                   space.wrap(stop)))
        return s

# ____________________________________________________________

class SubBufferMixin(object):
    _mixin_ = True

    def __init__(self, buffer, offset, size):
        self.buffer = buffer
        self.offset = offset
        self.size = size

    def getlength(self):
        at_most = self.buffer.getlength() - self.offset
        if 0 <= self.size <= at_most:
            return self.size
        elif at_most >= 0:
            return at_most
        else:
            return 0

    def getitem(self, index):
        return self.buffer.getitem(self.offset + index)

    def getslice(self, start, stop, step, size):
        if start == stop:
            return ''     # otherwise, adding self.offset might make them
                          # out of bounds
        return self.buffer.getslice(self.offset + start, self.offset + stop, step, size)

class SubBuffer(SubBufferMixin, Buffer):
    pass

class RWSubBuffer(SubBufferMixin, RWBuffer):

    def setitem(self, index, char):
        self.buffer.setitem(self.offset + index, char)

    def setslice(self, start, string):
        if len(string) == 0:
            return        # otherwise, adding self.offset might make 'start'
                          # out of bounds
        self.buffer.setslice(self.offset + start, string)
