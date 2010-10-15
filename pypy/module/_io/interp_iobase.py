from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.typedef import (
    TypeDef, GetSetProperty, generic_new_descr)
from pypy.interpreter.gateway import interp2app, Arguments, unwrap_spec
from pypy.interpreter.error import OperationError

class W_IOBase(Wrappable):
    def __init__(self, space):
        # XXX: IOBase thinks it has to maintain its own internal state in
        # `__IOBase_closed` and call flush() by itself, but it is redundant
        # with whatever behaviour a non-trivial derived class will implement.
        self.__IOBase_closed = False

    def _closed(self, space):
        # This gets the derived attribute, which is *not* __IOBase_closed
        # in most cases!
        w_closed = space.findattr(self, space.wrap('closed'))
        if w_closed is not None and space.is_true(w_closed):
            return True
        return False

    def _CLOSED(self):
        # Use this macro whenever you want to check the internal `closed`
        # status of the IOBase object rather than the virtual `closed`
        # attribute as returned by whatever subclass.
        return self.__IOBase_closed

    def _check_closed(self, space):
        if self._closed(space):
            raise OperationError(
                space.w_ValueError,
                space.wrap("I/O operation on closed file"))

    def closed_get_w(space, self):
        return space.newbool(self.__IOBase_closed)

    @unwrap_spec('self', ObjSpace)
    def close_w(self, space):
        if self._CLOSED():
            return
        try:
            space.call_method(self, "flush")
        finally:
            self.__IOBase_closed = True

    @unwrap_spec('self', ObjSpace)
    def flush_w(self, space):
        if self._CLOSED():
            raise OperationError(
                space.w_ValueError,
                space.wrap("I/O operation on closed file"))

    @unwrap_spec('self', ObjSpace)
    def enter_w(self, space):
        self._check_closed(space)
        return space.wrap(self)

    @unwrap_spec('self', ObjSpace, Arguments)
    def exit_w(self, space, __args__):
        space.call_method(self, "close")

    @unwrap_spec('self', ObjSpace)
    def iter_w(self, space):
        self._check_closed(space)
        return space.wrap(self)

    @unwrap_spec('self', ObjSpace)
    def next_w(self, space):
        w_line = space.call_method(self, "readline")
        if space.int_w(space.len(w_line)) == 0:
            raise OperationError(space.w_StopIteration, space.w_None)
        return w_line

    @unwrap_spec('self', ObjSpace)
    def isatty_w(self, space):
        return space.w_False

    @unwrap_spec('self', ObjSpace)
    def readable_w(self, space):
        return space.w_False

    @unwrap_spec('self', ObjSpace)
    def writable_w(self, space):
        return space.w_False

    @unwrap_spec('self', ObjSpace)
    def seekable_w(self, space):
        return space.w_False

W_IOBase.typedef = TypeDef(
    '_IOBase',
    __new__ = generic_new_descr(W_IOBase),
    __enter__ = interp2app(W_IOBase.enter_w),
    __exit__ = interp2app(W_IOBase.exit_w),
    __iter__ = interp2app(W_IOBase.iter_w),
    next = interp2app(W_IOBase.next_w),
    close = interp2app(W_IOBase.close_w),
    flush = interp2app(W_IOBase.flush_w),
    isatty = interp2app(W_IOBase.isatty_w),
    readable = interp2app(W_IOBase.readable_w),
    writable = interp2app(W_IOBase.writable_w),
    seekable = interp2app(W_IOBase.seekable_w),
    closed = GetSetProperty(W_IOBase.closed_get_w),
    )

class W_RawIOBase(W_IOBase):
    pass
W_RawIOBase.typedef = TypeDef(
    '_RawIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_RawIOBase),
    )

