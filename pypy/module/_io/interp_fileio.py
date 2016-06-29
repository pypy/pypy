from pypy.interpreter.typedef import TypeDef, interp_attrproperty, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import (
    OperationError, oefmt, wrap_oserror, wrap_oserror2)
from rpython.rlib.rarithmetic import r_longlong
from rpython.rlib.rstring import StringBuilder
from os import O_RDONLY, O_WRONLY, O_RDWR, O_CREAT, O_TRUNC
import sys, os, stat, errno
from pypy.module._io.interp_iobase import W_RawIOBase, convert_size

def interp_member_w(name, cls, doc=None):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, obj):
        w_value = getattr(obj, name)
        if w_value is None:
            raise OperationError(space.w_AttributeError, space.wrap(name))
        else:
            return w_value
    def fset(space, obj, w_value):
        setattr(obj, name, w_value)
    def fdel(space, obj):
        w_value = getattr(obj, name)
        if w_value is None:
            raise OperationError(space.w_AttributeError, space.wrap(name))
        setattr(obj, name, None)

    return GetSetProperty(fget, fset, fdel, cls=cls, doc=doc)


O_BINARY = getattr(os, "O_BINARY", 0)
O_APPEND = getattr(os, "O_APPEND", 0)

def _bad_mode(space):
    raise oefmt(space.w_ValueError,
                "Must have exactly one of read/write/append mode")

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
            append = True
            flags |= O_APPEND | O_CREAT
        elif s == 'b':
            pass
        elif s == '+':
            if plus:
                _bad_mode(space)
            readable = writable = True
            plus = True
        else:
            raise oefmt(space.w_ValueError, "invalid mode: %s", mode)

    if not rwa:
        _bad_mode(space)

    if readable and writable:
        flags |= O_RDWR
    elif readable:
        flags |= O_RDONLY
    else:
        flags |= O_WRONLY

    flags |= O_BINARY

    return readable, writable, append, flags

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

class W_FileIO(W_RawIOBase):
    def __init__(self, space):
        W_RawIOBase.__init__(self, space)
        self.fd = -1
        self.readable = False
        self.writable = False
        self.appending = False
        self.seekable = -1
        self.closefd = True
        self.w_name = None

    def descr_new(space, w_subtype, __args__):
        self = space.allocate_instance(W_FileIO, w_subtype)
        W_FileIO.__init__(self, space)
        return space.wrap(self)

    @unwrap_spec(mode=str, closefd=int)
    def descr_init(self, space, w_name, mode='r', closefd=True):
        if space.isinstance_w(w_name, space.w_float):
            raise oefmt(space.w_TypeError,
                        "integer argument expected, got float")

        fd = -1
        try:
            fd = space.c_int_w(w_name)
        except OperationError as e:
            pass
        else:
            if fd < 0:
                raise oefmt(space.w_ValueError, "negative file descriptor")

        self.readable, self.writable, self.appending, flags = decode_mode(space, mode)

        fd_is_own = False
        try:
            if fd >= 0:
                try:
                    os.fstat(fd)
                except OSError as e:
                    if e.errno == errno.EBADF:
                        raise wrap_oserror(space, e)
                    # else: pass
                self.fd = fd
                self.closefd = bool(closefd)
            else:
                self.closefd = True
                if not closefd:
                    raise oefmt(space.w_ValueError,
                                "Cannot use closefd=False with file name")

                from pypy.module.posix.interp_posix import (
                    dispatch_filename, rposix)
                try:
                    self.fd = dispatch_filename(rposix.open)(
                        space, w_name, flags, 0666)
                except OSError as e:
                    raise wrap_oserror2(space, e, w_name,
                                        exception_name='w_IOError')
                finally:
                    fd_is_own = True

            self._dircheck(space, w_name)
            space.setattr(self, space.wrap("name"), w_name)

            if self.appending:
                # For consistent behaviour, we explicitly seek to the end of file
                # (otherwise, it might be done only on the first write()).
                try:
                    os.lseek(self.fd, 0, os.SEEK_END)
                except OSError as e:
                    raise wrap_oserror(space, e, exception_name='w_IOError')
        except:
            if not fd_is_own:
                self.fd = -1
            raise

    def _mode(self):
        if self.appending:
            if self.readable:
                return 'ab+'
            else:
                return 'ab'
        elif self.readable:
            if self.writable:
                return 'rb+'
            else:
                return 'rb'
        else:
            return 'wb'

    def descr_get_mode(self, space):
        return space.wrap(self._mode())

    def _closed(self, space):
        return self.fd < 0

    def _check_closed(self, space, message=None):
        if message is None:
            message = "I/O operation on closed file"
        if self.fd < 0:
            raise OperationError(space.w_ValueError, space.wrap(message))

    def _check_readable(self, space):
        if not self.readable:
            raise oefmt(space.w_ValueError, "file not open for reading")

    def _check_writable(self, space):
        if not self.writable:
            raise oefmt(space.w_ValueError, "file not open for writing")

    def _close(self, space):
        if self.fd < 0:
            return
        fd = self.fd
        self.fd = -1

        try:
            os.close(fd)
        except OSError as e:
            raise wrap_oserror(space, e,
                               exception_name='w_IOError')

    def close_w(self, space):
        try:
            W_RawIOBase.close_w(self, space)
        except OperationError:
            if not self.closefd:
                self.fd = -1
                raise
            self._close(space)
            raise
        if not self.closefd:
            self.fd = -1
            return
        self._close(space)

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
            raise wrap_oserror2(space, OSError(errno.EISDIR, "fstat"),
                                w_filename, exception_name='w_IOError')

    @unwrap_spec(pos=r_longlong, whence=int)
    def seek_w(self, space, pos, whence=0):
        self._check_closed(space)
        try:
            pos = os.lseek(self.fd, pos, whence)
        except OSError as e:
            raise wrap_oserror(space, e,
                               exception_name='w_IOError')
        return space.wrap(pos)

    def tell_w(self, space):
        self._check_closed(space)
        try:
            pos = os.lseek(self.fd, 0, 1)
        except OSError as e:
            raise wrap_oserror(space, e,
                               exception_name='w_IOError')
        return space.wrap(pos)

    def readable_w(self, space):
        self._check_closed(space)
        return space.wrap(self.readable)

    def writable_w(self, space):
        self._check_closed(space)
        return space.wrap(self.writable)

    def seekable_w(self, space):
        self._check_closed(space)
        if self.seekable < 0:
            try:
                os.lseek(self.fd, 0, os.SEEK_CUR)
            except OSError:
                self.seekable = 0
            else:
                self.seekable = 1
        return space.newbool(self.seekable == 1)

    # ______________________________________________

    def fileno_w(self, space):
        self._check_closed(space)
        return space.wrap(self.fd)

    def isatty_w(self, space):
        self._check_closed(space)
        try:
            res = os.isatty(self.fd)
        except OSError as e:
            raise wrap_oserror(space, e, exception_name='w_IOError')
        return space.wrap(res)

    def repr_w(self, space):
        if self.fd < 0:
            return space.wrap("<_io.FileIO [closed]>")

        if self.w_name is None:
            return space.wrap(
                "<_io.FileIO fd=%d mode='%s'>" % (
                    self.fd, self._mode()))
        else:
            w_repr = space.repr(self.w_name)
            return space.wrap(
                "<_io.FileIO name=%s mode='%s'>" % (
                    space.str_w(w_repr), self._mode()))

    # ______________________________________________

    def write_w(self, space, w_data):
        self._check_closed(space)
        self._check_writable(space)
        data = space.getarg_w('s*', w_data).as_str()

        try:
            n = os.write(self.fd, data)
        except OSError as e:
            if e.errno == errno.EAGAIN:
                return space.w_None
            raise wrap_oserror(space, e,
                               exception_name='w_IOError')

        return space.wrap(n)

    def read_w(self, space, w_size=None):
        self._check_closed(space)
        self._check_readable(space)
        size = convert_size(space, w_size)

        if size < 0:
            return self.readall_w(space)

        try:
            s = os.read(self.fd, size)
        except OSError as e:
            if e.errno == errno.EAGAIN:
                return space.w_None
            raise wrap_oserror(space, e,
                               exception_name='w_IOError')

        return space.newbytes(s)

    def readinto_w(self, space, w_buffer):
        self._check_closed(space)
        self._check_readable(space)
        rwbuffer = space.getarg_w('w*', w_buffer)
        length = rwbuffer.getlength()
        try:
            buf = os.read(self.fd, length)
        except OSError as e:
            if e.errno == errno.EAGAIN:
                return space.w_None
            raise wrap_oserror(space, e,
                               exception_name='w_IOError')
        rwbuffer.setslice(0, buf)
        return space.wrap(len(buf))

    def readall_w(self, space):
        self._check_closed(space)
        self._check_readable(space)
        total = 0

        builder = StringBuilder()
        while True:
            newsize = int(new_buffersize(self.fd, total))

            try:
                chunk = os.read(self.fd, newsize - total)
            except OSError as e:
                if e.errno == errno.EINTR:
                    space.getexecutioncontext().checksignals()
                    continue
                if total > 0:
                    # return what we've got so far
                    break
                if e.errno == errno.EAGAIN:
                    return space.w_None
                raise wrap_oserror(space, e,
                                   exception_name='w_IOError')

            if not chunk:
                break
            builder.append(chunk)
            total += len(chunk)
        return space.newbytes(builder.build())

    if sys.platform == "win32":
        def _truncate(self, size):
            from rpython.rlib.streamio import ftruncate_win32
            ftruncate_win32(self.fd, size)
    else:
        def _truncate(self, size):
            os.ftruncate(self.fd, size)

    def truncate_w(self, space, w_size=None):
        self._check_closed(space)
        self._check_writable(space)
        if space.is_none(w_size):
            w_size = self.tell_w(space)

        try:
            self._truncate(space.r_longlong_w(w_size))
        except OSError as e:
            raise wrap_oserror(space, e, exception_name='w_IOError')

        return w_size

W_FileIO.typedef = TypeDef(
    '_io.FileIO', W_RawIOBase.typedef,
    __new__  = interp2app(W_FileIO.descr_new.im_func),
    __init__  = interp2app(W_FileIO.descr_init),
    __repr__ = interp2app(W_FileIO.repr_w),

    seek = interp2app(W_FileIO.seek_w),
    tell = interp2app(W_FileIO.tell_w),
    write = interp2app(W_FileIO.write_w),
    read = interp2app(W_FileIO.read_w),
    readinto = interp2app(W_FileIO.readinto_w),
    readall = interp2app(W_FileIO.readall_w),
    truncate = interp2app(W_FileIO.truncate_w),
    close = interp2app(W_FileIO.close_w),

    readable = interp2app(W_FileIO.readable_w),
    writable = interp2app(W_FileIO.writable_w),
    seekable = interp2app(W_FileIO.seekable_w),
    fileno = interp2app(W_FileIO.fileno_w),
    isatty = interp2app(W_FileIO.isatty_w),
    name = interp_member_w('w_name', cls=W_FileIO),
    closefd = interp_attrproperty('closefd', cls=W_FileIO),
    mode = GetSetProperty(W_FileIO.descr_get_mode),
    )

