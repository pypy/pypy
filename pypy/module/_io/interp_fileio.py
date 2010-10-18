from pypy.module._io.interp_iobase import W_RawIOBase
from pypy.interpreter.typedef import (
    TypeDef, interp_attrproperty_w, GetSetProperty)
from pypy.interpreter.gateway import interp2app, unwrap_spec, Arguments
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError, wrap_oserror2
from pypy.rlib.rarithmetic import r_longlong
from os import O_RDONLY, O_WRONLY, O_RDWR, O_CREAT, O_TRUNC
import os

O_BINARY = getattr(os, "O_BINARY", 0)
O_APPEND = getattr(os, "O_APPEND", 0)

def _bad_mode(space):
    raise OperationError(space.w_ValueError, space.wrap(
        "Must have exactly one of read/write/append mode"))

def decode_mode(space, mode):
    flags = 0
    rwa = False
    readable = False
    writable = False
    append = False
    plus = False

    for s in mode:
        if s == 'r':
            if rwa:
                _bad_mode(space)
            rwa = True
            readable = True
        elif s == 'w':
            if rwa:
                _bad_mode(space)
            rwa = True
            writable = True
            flags |= O_CREAT | O_TRUNC
        elif s == 'a':
            if rwa:
                _bad_mode(space)
            rwa = True
            writable = True
            flags |= O_CREAT
            append = True
        elif s == 'b':
            pass
        elif s == '+':
            if plus:
                _bad_mode(space)
            readable = writable = True
            plus = True
        else:
            raise OperationError(space.w_ValueError, space.wrap(
                "invalid mode: %s" % (mode,)))

    if not rwa:
        _bad_mode(space)

    if readable and writable:
        flags |= O_RDWR
    elif readable:
        flags |= O_RDONLY
    else:
        flags |= O_WRONLY

    flags |= O_BINARY

    if append:
        flags |= O_APPEND

    return readable, writable, flags

class W_FileIO(W_RawIOBase):
    def __init__(self, space):
        W_RawIOBase.__init__(self, space)
        self.fd = -1
        self.readable = False
        self.writable = False
        self.seekable = -1
        self.closefd = True
        self.w_name = None

    @unwrap_spec(ObjSpace, W_Root, Arguments)
    def descr_new(space, w_subtype, __args__):
        self = space.allocate_instance(W_FileIO, w_subtype)
        W_FileIO.__init__(self, space)
        return space.wrap(self)

    @unwrap_spec('self', ObjSpace, W_Root, str, int)
    def descr_init(self, space, w_name, mode='r', closefd=True):
        if space.isinstance_w(w_name, space.w_float):
            raise OperationError(space.w_TypeError, space.wrap(
                "integer argument expected, got float"))

        fd = -1
        try:
            fd = space.int_w(w_name)
        except OperationError, e:
            pass
        else:
            if fd < 0:
                raise OperationError(space.w_ValueError, space.wrap(
                    "negative file descriptor"))

        self.readable, self.writable, flags = decode_mode(space, mode)

        if fd >= 0:
            self.fd = fd
        else:
            from pypy.module.posix.interp_posix import (
                dispatch_filename, rposix)
            try:
                self.fd = dispatch_filename(rposix.open)(
                    space, w_name, flags, 0666)
            except OSError, e:
                raise wrap_oserror2(space, e, w_name)
        self.closefd = bool(closefd)
        self.w_name = w_name

    def _mode(self):
        if self.readable:
            if self.writable:
                return 'rb+'
            else:
                return 'rb'
        else:
            return 'wb'

    def descr_get_mode(space, self):
        return space.wrap(self._mode())

    def _check_closed(self, space):
        if self.fd < 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "I/O operation on closed file"))

    @unwrap_spec('self', ObjSpace, r_longlong, int)
    def seek_w(self, space, pos, whence):
        self._check_closed(space)
        pos = os.lseek(self.fd, pos, whence)
        return space.wrap(pos)

    @unwrap_spec('self', ObjSpace)
    def readable_w(self, space):
        self._check_closed(space)
        return space.wrap(self.readable)

    @unwrap_spec('self', ObjSpace)
    def writable_w(self, space):
        self._check_closed(space)
        return space.wrap(self.writable)

    @unwrap_spec('self', ObjSpace)
    def seekable_w(self, space):
        self._check_closed(space)
        if self.seekable < 0:
            try:
                pos = os.lseek(self.fd, 0, os.SEEK_CUR)
            except OSError:
                self.seekable = 0
            else:
                self.seekable = 1
        return space.newbool(self.seekable == 1)

W_FileIO.typedef = TypeDef(
    'FileIO', W_RawIOBase.typedef,
    __new__  = interp2app(W_FileIO.descr_new.im_func),
    __init__  = interp2app(W_FileIO.descr_init),

    seek = interp2app(W_FileIO.seek_w),

    readable = interp2app(W_FileIO.readable_w),
    writable = interp2app(W_FileIO.writable_w),
    seekable = interp2app(W_FileIO.seekable_w),
    name = interp_attrproperty_w('w_name', cls=W_FileIO),
    mode = GetSetProperty(W_FileIO.descr_get_mode),
    )

