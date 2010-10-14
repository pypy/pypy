from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.typedef import (
    TypeDef, interp_attrproperty, GetSetProperty, generic_new_descr)
from pypy.interpreter.gateway import interp2app, Arguments, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.module.exceptions.interp_exceptions import W_IOError
from pypy.tool.sourcetools import func_renamer

DEFAULT_BUFFER_SIZE = 8192

class W_BlockingIOError(W_IOError):
    def __init__(self, space):
        W_IOError.__init__(self, space)
        self.written = 0

    @unwrap_spec('self', ObjSpace, W_Root, W_Root, int)
    def descr_init(self, space, w_errno, w_strerror, written=0):
        W_IOError.descr_init(self, space, [w_errno, w_strerror])
        self.written = written

W_BlockingIOError.typedef = TypeDef(
    'BlockingIOError',
    __doc__ = ("Exception raised when I/O would block "
               "on a non-blocking I/O stream"),
    __new__  = generic_new_descr(W_BlockingIOError),
    __init__ = interp2app(W_BlockingIOError.descr_init),
    characters_written = interp_attrproperty('written', W_BlockingIOError),
    )

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

class W_BufferedIOBase(W_IOBase):
    pass

W_BufferedIOBase.typedef = TypeDef(
    '_BufferedIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_BufferedIOBase),
    )

class W_TextIOBase(W_IOBase):
    pass
W_TextIOBase.typedef = TypeDef(
    '_TextIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_TextIOBase),
    )

class W_BytesIO(W_BufferedIOBase):
    pass
W_BytesIO.typedef = TypeDef(
    'BytesIO', W_BufferedIOBase.typedef,
    )

class W_BufferedReader(W_BufferedIOBase):
    pass
W_BufferedReader.typedef = TypeDef(
    'BufferedReader', W_BufferedIOBase.typedef,
    )

class W_BufferedWriter(W_BufferedIOBase):
    pass
W_BufferedWriter.typedef = TypeDef(
    'BufferedWriter', W_BufferedIOBase.typedef,
    )

class W_BufferedRWPair(W_BufferedIOBase):
    pass
W_BufferedRWPair.typedef = TypeDef(
    'BufferedRWPair', W_BufferedIOBase.typedef,
    )

class W_BufferedRandom(W_BufferedIOBase):
    pass
W_BufferedRandom.typedef = TypeDef(
    'BufferedRandom', W_BufferedIOBase.typedef,
    )

class W_TextIOWrapper(W_TextIOBase):
    pass
W_TextIOWrapper.typedef = TypeDef(
    'TextIOWrapper', W_TextIOBase.typedef,
    )

@unwrap_spec(ObjSpace, Arguments)
def open(space, __args__):
    # XXX cheat!
    w_pyio = space.call_method(space.builtin, '__import__',
                             space.wrap("_pyio"))
    w_func = space.getattr(w_pyio, space.wrap("open"))
    return space.call_args(w_func, __args__)

