from pypy.module._io.interp_iobase import W_RawIOBase
from pypy.interpreter.typedef import (
    TypeDef, interp_attrproperty_w, GetSetProperty)
from pypy.interpreter.gateway import interp2app, unwrap_spec, Arguments
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError, wrap_oserror, wrap_oserror2
from pypy.rlib.rarithmetic import r_longlong
from pypy.rlib.rstring import StringBuilder
from os import O_RDONLY, O_WRONLY, O_RDWR, O_CREAT, O_TRUNC
import os, stat, errno

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

    return readable, writable, append, flags

def convert_size(space, w_size):
    if space.is_w(w_size, space.w_None):
        return -1
    else:
        return space.int_w(w_size)

SMALLCHUNK = 8 * 1024
BIGCHUNK = 512 * 1024

def new_buffersize(fd, currentsize):
    try:
        st = os.fstat(fd)
        end = st.st_size
        pos = os.lseek(fd, 0, 1)
    except OSError:
        pass
    else:
        # Files claiming a size smaller than SMALLCHUNK may
        # actually be streaming pseudo-files. In this case, we
        # apply the more aggressive algorithm below.
        if end >= SMALLCHUNK and end >= pos:
            # Add 1 so if the file were to grow we'd notice.
            return currentsize + end - pos + 1

    if currentsize > SMALLCHUNK:
        # Keep doubling until we reach BIGCHUNK;
        # then keep adding BIGCHUNK.
        if currentsize <= BIGCHUNK:
            return currentsize + currentsize
        else:
            return currentsize + BIGCHUNK
    return currentsize + SMALLCHUNK

def verify_fd(fd):
    return

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

        self.readable, self.writable, append, flags = decode_mode(space, mode)

        if fd >= 0:
            verify_fd(fd)
            try:
                os.fstat(fd)
            except OSError, e:
                if e.errno == errno.EBADF:
                    raise wrap_oserror(space, e)
                # else: pass
            self.fd = fd
            self.closefd = bool(closefd)
        else:
            if not closefd:
                raise OperationError(space.w_ValueError, space.wrap(
                    "Cannot use closefd=False with file name"))
            self.closefd = True

            from pypy.module.posix.interp_posix import (
                dispatch_filename, rposix)
            try:
                self.fd = dispatch_filename(rposix.open)(
                    space, w_name, flags, 0666)
            except OSError, e:
                raise wrap_oserror2(space, e, w_name,
                                    exception_name='w_IOError')

            self._dircheck(space, w_name)
        self.w_name = w_name

        if append:
            # For consistent behaviour, we explicitly seek to the end of file
            # (otherwise, it might be done only on the first write()).
            try:
                os.lseek(self.fd, 0, os.SEEK_END)
            except OSError, e:
                raise wrap_oserror(space, e)

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

    def _close(self, space):
        if self.fd < 0:
            return
        fd = self.fd
        self.fd = -1

        try:
            verify_fd(fd)
            os.close(fd)
        except OSError, e:
            raise wrap_oserror(space, e,
                               exception_name='w_IOError')

    @unwrap_spec('self', ObjSpace)
    def close_w(self, space):
        if not self.closefd:
            self.fd = -1
            return
        self._close(space)
        W_RawIOBase.close_w(self, space)

    def _dircheck(self, space, w_filename):
        # On Unix, fopen will succeed for directories.
        # In Python, there should be no file objects referring to
        # directories, so we need a check.
        if self.fd < 0:
            return
        try:
            st = os.fstat(self.fd)
        except OSError:
            return
        if stat.S_ISDIR(st.st_mode):
            self._close(space)
            raise wrap_oserror2(space, OSError(errno.EISDIR, "fstat"),
                                w_filename, exception_name='w_IOError')

    @unwrap_spec('self', ObjSpace, r_longlong, int)
    def seek_w(self, space, pos, whence=0):
        self._check_closed(space)
        try:
            pos = os.lseek(self.fd, pos, whence)
        except OSError, e:
            raise wrap_oserror(space, e,
                               exception_name='w_IOError')
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

    # ______________________________________________

    @unwrap_spec('self', ObjSpace)
    def fileno_w(self, space):
        self._check_closed(space)
        return space.wrap(self.fd)

    @unwrap_spec('self', ObjSpace)
    def isatty_w(self, space):
        self._check_closed(space)
        try:
            res = os.isatty(self.fd)
        except OSError, e:
            raise wrap_oserror(space, e)
        return space.wrap(res)

    # ______________________________________________

    @unwrap_spec('self', ObjSpace, W_Root)
    def write_w(self, space, w_data):
        self._check_closed(space)
        # XXX self._check_writable(space)
        data = space.str_w(w_data)

        try:
            n = os.write(self.fd, data)
        except OSError, e:
            raise wrap_oserror(space, e,
                               exception_name='w_IOError')

        return space.wrap(n)

    @unwrap_spec('self', ObjSpace, W_Root)
    def read_w(self, space, w_size=None):
        self._check_closed(space)
        # XXX self._check_readable(space)
        size = convert_size(space, w_size)

        if size < 0:
            return self.readall_w(space)

        try:
            s = os.read(self.fd, size)
        except OSError, e:
            raise wrap_oserror(space, e,
                               exception_name='w_IOError')

        return space.wrap(s)

    @unwrap_spec('self', ObjSpace)
    def readall_w(self, space):
        self._check_closed(space)
        total = 0

        builder = StringBuilder()
        while True:
            newsize = int(new_buffersize(self.fd, total))

            try:
                chunk = os.read(self.fd, newsize - total)
            except OSError, e:
                if e.errno == errno.EAGAIN:
                    if total > 0:
                        # return what we've got so far
                        break
                    return space.w_None
                raise wrap_oserror(space, e,
                                   exception_name='w_IOError')

            if not chunk:
                break
            builder.append(chunk)
            total += len(chunk)
        return space.wrap(builder.build())


W_FileIO.typedef = TypeDef(
    'FileIO', W_RawIOBase.typedef,
    __new__  = interp2app(W_FileIO.descr_new.im_func),
    __init__  = interp2app(W_FileIO.descr_init),

    seek = interp2app(W_FileIO.seek_w),
    write = interp2app(W_FileIO.write_w),
    read = interp2app(W_FileIO.read_w),
    readall = interp2app(W_FileIO.readall_w),
    close = interp2app(W_FileIO.close_w),

    readable = interp2app(W_FileIO.readable_w),
    writable = interp2app(W_FileIO.writable_w),
    seekable = interp2app(W_FileIO.seekable_w),
    fileno = interp2app(W_FileIO.fileno_w),
    isatty = interp2app(W_FileIO.isatty_w),
    name = interp_attrproperty_w('w_name', cls=W_FileIO),
    mode = GetSetProperty(W_FileIO.descr_get_mode),
    )

