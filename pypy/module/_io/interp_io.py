import os

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import (
    TypeDef, interp_attrproperty, generic_new_descr)
from pypy.module.exceptions.interp_exceptions import W_IOError
from pypy.module._io.interp_fileio import W_FileIO
from pypy.module._io.interp_textio import W_TextIOWrapper
from rpython.rlib.rposix_stat import STAT_FIELD_TYPES

HAS_BLKSIZE = 'st_blksize' in STAT_FIELD_TYPES


class Cache:
    def __init__(self, space):
        self.w_unsupportedoperation = space.new_exception_class(
            "io.UnsupportedOperation",
            space.newtuple([space.w_ValueError, space.w_IOError]))

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
    __doc__ = ("Exception raised when I/O would block on a non-blocking "
               "I/O stream"),
    __new__  = generic_new_descr(W_BlockingIOError),
    __init__ = interp2app(W_BlockingIOError.descr_init),
    characters_written = interp_attrproperty('written', W_BlockingIOError,
        wrapfn="newint"),
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
        raise oefmt(space.w_TypeError, "invalid file: %R", w_file)

    reading = writing = appending = updating = text = binary = universal = False

    uniq_mode = {}
    for flag in mode:
        uniq_mode[flag] = None
    if len(uniq_mode) != len(mode):
        raise oefmt(space.w_ValueError, "invalid mode: %s", mode)
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
            raise oefmt(space.w_ValueError, "invalid mode: %s", mode)

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
        raise oefmt(space.w_ValueError, "can't use U and writing mode at once")
    if text and binary:
        raise oefmt(space.w_ValueError,
                    "can't have text and binary mode at once")
    if reading + writing + appending > 1:
        raise oefmt(space.w_ValueError,
                    "must have exactly one of read/write/append mode")
    if binary and encoding is not None:
        raise oefmt(space.w_ValueError,
                    "binary mode doesn't take an encoding argument")
    if binary and newline is not None:
        raise oefmt(space.w_ValueError,
                    "binary mode doesn't take a newline argument")
    w_raw = space.call_function(
        space.gettypefor(W_FileIO), w_file, space.newtext(rawmode), space.newbool(closefd)
    )

    isatty = space.is_true(space.call_method(w_raw, "isatty"))
    line_buffering = buffering == 1 or (buffering < 0 and isatty)
    if line_buffering:
        buffering = -1

    if buffering < 0:
        buffering = DEFAULT_BUFFER_SIZE

        if HAS_BLKSIZE:
            fileno = space.c_int_w(space.call_method(w_raw, "fileno"))
            try:
                st = os.fstat(fileno)
            except OSError:
                # Errors should never pass silently, except this one time.
                pass
            else:
                if st.st_blksize > 1:
                    buffering = st.st_blksize

    if buffering < 0:
        raise oefmt(space.w_ValueError, "invalid buffering size")

    if buffering == 0:
        if not binary:
            raise oefmt(space.w_ValueError, "can't have unbuffered text I/O")
        return w_raw

    if updating:
        buffer_cls = W_BufferedRandom
    elif writing or appending:
        buffer_cls = W_BufferedWriter
    elif reading:
        buffer_cls = W_BufferedReader
    else:
        raise oefmt(space.w_ValueError, "unknown mode: '%s'", mode)
    w_buffer = space.call_function(
        space.gettypefor(buffer_cls), w_raw, space.newint(buffering)
    )
    if binary:
        return w_buffer

    w_wrapper = space.call_function(space.gettypefor(W_TextIOWrapper),
        w_buffer,
        space.newtext_or_none(encoding),
        space.newtext_or_none(errors),
        space.newtext_or_none(newline),
        space.newbool(line_buffering)
    )
    space.setattr(w_wrapper, space.newtext("mode"), space.newtext(mode))
    return w_wrapper
