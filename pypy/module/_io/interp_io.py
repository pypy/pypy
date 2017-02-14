import os

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import (
    TypeDef, interp_attrproperty, generic_new_descr)
from pypy.module._io.interp_fileio import W_FileIO
from pypy.module._io.interp_textio import W_TextIOWrapper


class Cache:
    def __init__(self, space):
        self.w_unsupportedoperation = space.new_exception_class(
            "io.UnsupportedOperation",
            space.newtuple([space.w_ValueError, space.w_IOError]))

@unwrap_spec(mode=str, buffering=int,
             encoding="str_or_None", errors="str_or_None",
             newline="str_or_None", closefd=int)
def open(space, w_file, mode="r", buffering=-1, encoding=None, errors=None,
         newline=None, closefd=True, w_opener=None):
    from pypy.module._io.interp_bufferedio import (W_BufferedRandom,
        W_BufferedWriter, W_BufferedReader)

    if not (space.isinstance_w(w_file, space.w_unicode) or
            space.isinstance_w(w_file, space.w_str) or
            space.isinstance_w(w_file, space.w_int)):
        raise oefmt(space.w_TypeError, "invalid file: %R", w_file)

    reading = writing = creating = appending = updating = text = binary = universal = False

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
        elif flag == "x":
            creating = True
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
    if creating:
        rawmode += "x"
    if appending:
        rawmode += "a"
    if updating:
        rawmode += "+"

    if universal:
        if writing or appending:
            raise oefmt(space.w_ValueError,
                        "can't use U and writing mode at once")
        space.warn(space.newtext("'U' mode is deprecated ('r' has the same "
                              "effect in Python 3.x)"),
                   space.w_DeprecationWarning)
    if text and binary:
        raise oefmt(space.w_ValueError,
                    "can't have text and binary mode at once")
    if reading + writing + creating + appending > 1:
        raise oefmt(space.w_ValueError,
                    "must have exactly one of read/write/create/append mode")
    if binary and encoding is not None:
        raise oefmt(space.w_ValueError,
                    "binary mode doesn't take an encoding argument")
    if binary and newline is not None:
        raise oefmt(space.w_ValueError,
                    "binary mode doesn't take a newline argument")
    w_raw = space.call_function(
        space.gettypefor(W_FileIO), w_file, space.newtext(rawmode),
        space.newbool(closefd), w_opener)

    isatty = space.is_true(space.call_method(w_raw, "isatty"))
    line_buffering = buffering == 1 or (buffering < 0 and isatty)
    if line_buffering:
        buffering = -1

    if buffering < 0:
        buffering = space.c_int_w(space.getattr(w_raw, space.newtext("_blksize")))

    if buffering < 0:
        raise oefmt(space.w_ValueError, "invalid buffering size")

    if buffering == 0:
        if not binary:
            raise oefmt(space.w_ValueError, "can't have unbuffered text I/O")
        return w_raw

    if updating:
        buffer_cls = W_BufferedRandom
    elif writing or creating or appending:
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
