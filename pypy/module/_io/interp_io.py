import os

from pypy.interpreter.error import operationerrfmt, OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import (
    TypeDef, interp_attrproperty, generic_new_descr)
from pypy.module.exceptions.interp_exceptions import W_IOError
from pypy.module._io.interp_fileio import W_FileIO
from pypy.module._io.interp_iobase import W_IOBase
from pypy.module._io.interp_textio import W_TextIOWrapper
from pypy.rpython.module.ll_os_stat import STAT_FIELD_TYPES


class W_BlockingIOError(W_IOError):
    def __init__(self, space):
        W_IOError.__init__(self, space)
        self.written = 0

    @unwrap_spec(written=int)
    def descr_init(self, space, w_errno, w_strerror, written=0):
        W_IOError.descr_init(self, space, [w_errno, w_strerror])
        self.written = written

W_BlockingIOError.typedef = TypeDef(
    'BlockingIOError', W_IOError.typedef,
    __doc__ = ("Exception raised when I/O would block "
               "on a non-blocking I/O stream"),
    __new__  = generic_new_descr(W_BlockingIOError),
    __init__ = interp2app(W_BlockingIOError.descr_init),
    characters_written = interp_attrproperty('written', W_BlockingIOError),
    )

DEFAULT_BUFFER_SIZE = 8 * 1024

@unwrap_spec(mode=str, buffering=int,
             encoding="str_or_None", errors="str_or_None",
             newline="str_or_None", closefd=bool)
def open(space, w_file, mode="r", buffering=-1, encoding=None, errors=None,
    newline=None, closefd=True):
    from pypy.module._io.interp_bufferedio import (W_BufferedRandom,
        W_BufferedWriter, W_BufferedReader)

    if not (space.isinstance_w(w_file, space.w_basestring) or
        space.isinstance_w(w_file, space.w_int) or
        space.isinstance_w(w_file, space.w_long)):
        raise operationerrfmt(space.w_TypeError,
            "invalid file: %s", space.str_w(space.repr(w_file))
        )

    reading = writing = appending = updating = text = binary = universal = False

    uniq_mode = {}
    for flag in mode:
        uniq_mode[flag] = None
    if len(uniq_mode) != len(mode):
        raise operationerrfmt(space.w_ValueError,
            "invalid mode: %s", mode
        )
    for flag in mode:
        if flag == "r":
            reading = True
        elif flag == "w":
            writing = True
        elif flag == "a":
            appending = True
        elif flag == "+":
            updating = True
        elif flag == "t":
            text = True
        elif flag == "b":
            binary = True
        elif flag == "U":
            universal = True
            reading = True
        else:
            raise operationerrfmt(space.w_ValueError,
                "invalid mode: %s", mode
            )

    rawmode = ""
    if reading:
        rawmode += "r"
    if writing:
        rawmode += "w"
    if appending:
        rawmode += "a"
    if updating:
        rawmode += "+"

    if universal and (writing or appending):
        raise OperationError(space.w_ValueError,
            space.wrap("can't use U and writing mode at once")
        )
    if text and binary:
        raise OperationError(space.w_ValueError,
            space.wrap("can't have text and binary mode at once")
        )
    if reading + writing + appending > 1:
        raise OperationError(space.w_ValueError,
            space.wrap("must have exactly one of read/write/append mode")
        )
    if binary and encoding is not None:
        raise OperationError(space.w_ValueError,
            space.wrap("binary mode doesn't take an errors argument")
        )
    if binary and newline is not None:
        raise OperationError(space.w_ValueError,
            space.wrap("binary mode doesn't take a newline argument")
        )
    w_raw = space.call_function(
        space.gettypefor(W_FileIO), w_file, space.wrap(rawmode), space.wrap(closefd)
    )

    isatty = space.is_true(space.call_method(w_raw, "isatty"))
    line_buffering = buffering == 1 or (buffering < 0 and isatty)
    if line_buffering:
        buffering = -1

    if buffering < 0:
        buffering = DEFAULT_BUFFER_SIZE

        if space.config.translation.type_system == 'lltype' and 'st_blksize' in STAT_FIELD_TYPES:
            fileno = space.int_w(space.call_method(w_raw, "fileno"))
            try:
                st = os.fstat(fileno)
            except OSError:
                # Errors should never pass silently, except this one time.
                pass
            else:
                if st.st_blksize > 1:
                    buffering = st.st_blksize

    if buffering < 0:
        raise OperationError(space.w_ValueError,
            space.wrap("invalid buffering size")
        )

    if buffering == 0:
        if not binary:
            raise OperationError(space.w_ValueError,
                space.wrap("can't have unbuffered text I/O")
            )
        return w_raw

    if updating:
        buffer_cls = W_BufferedRandom
    elif writing or appending:
        buffer_cls = W_BufferedWriter
    elif reading:
        buffer_cls = W_BufferedReader
    else:
        raise operationerrfmt(space.w_ValueError, "unknown mode: '%s'", mode)
    w_buffer = space.call_function(
        space.gettypefor(buffer_cls), w_raw, space.wrap(buffering)
    )
    if binary:
        return w_buffer

    w_wrapper = space.call_function(space.gettypefor(W_TextIOWrapper),
        w_buffer,
        space.wrap(encoding),
        space.wrap(errors),
        space.wrap(newline),
        space.wrap(line_buffering)
    )
    space.setattr(w_wrapper, space.wrap("mode"), space.wrap(mode))
    return w_wrapper
