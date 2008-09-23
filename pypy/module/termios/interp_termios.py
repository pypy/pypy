
""" Termios module. I'm implementing it directly here, as I see
little use of termios module on RPython level by itself
"""

from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.rpython.module import ll_termios
from pypy.rlib.objectmodel import we_are_translated
import os
from pypy.rlib import rtermios
import termios

# proper semantics are to have termios.error, but since it's not documented
# anyway, let's have it as OSError on interplevel. We need to have
# some details what is missing in RPython modules though

def convert_error(space, error):
    errno = error.errno
    w_module = space.getbuiltinmodule('termios')
    w_exception_class = space.getattr(w_module, space.wrap('error'))
    try:
        msg = os.strerror(errno)
    except ValueError:
        msg = 'error %d' % errno
    w_exception = space.call_function(w_exception_class, space.wrap(errno),
                                      space.wrap(msg))
    return OperationError(w_exception_class, w_exception)

def tcsetattr(space, fd, when, w_attributes):
    from pypy.interpreter.baseobjspace import UnpackValueError
    try:
        w_iflag, w_oflag, w_cflag, w_lflag, w_ispeed, w_ospeed, w_cc = \
                 space.unpackiterable(w_attributes, expected_length=7)
    except UnpackValueError, e:
        raise OperationError(
            space.w_TypeError,
            space.wrap("tcsetattr, arg 3: must be 7 element list"))
    w_builtin = space.getbuiltinmodule('__builtin__')
    cc = []
    for w_c in space.unpackiterable(w_cc):
        if space.is_true(space.isinstance(w_c, space.w_int)):
            ch = space.call_function(space.getattr(w_builtin,
                                          space.wrap('chr')), w_c)
            cc.append(space.str_w(ch))
        else:
            cc.append(space.str_w(w_c))
    tup = (space.int_w(w_iflag), space.int_w(w_oflag),
           space.int_w(w_cflag), space.int_w(w_lflag),
           space.int_w(w_ispeed), space.int_w(w_ospeed), cc)
    try:
        rtermios.tcsetattr(fd, when, tup)
    except termios.error, e:
        e.errno = e.args[0]
        raise convert_error(space, e)
tcsetattr.unwrap_spec = [ObjSpace, int, int, W_Root]

def tcgetattr(space, fd):
    try:
        tup = rtermios.tcgetattr(fd)
    except termios.error, e:
        e.errno = e.args[0]
        raise convert_error(space, e)
    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = tup
    l_w = [space.wrap(i) for i in [iflag, oflag, cflag, lflag, ispeed, ospeed]]
    # last one need to be chosen carefully
    cc_w = [space.wrap(i) for i in cc]
    if lflag & termios.ICANON:
        cc_w[termios.VMIN] = space.wrap(ord(cc[termios.VMIN]))
        cc_w[termios.VTIME] = space.wrap(ord(cc[termios.VTIME]))
    w_cc = space.newlist(cc_w)
    l_w.append(w_cc)
    return space.newlist(l_w)
tcgetattr.unwrap_spec = [ObjSpace, int]

def tcsendbreak(space, fd, duration):
    try:
        termios.tcsendbreak(fd, duration)
    except termios.error, e:
        e.errno = e.args[0]
        raise convert_error(space, e)
tcsendbreak.unwrap_spec = [ObjSpace, int, int]

def tcdrain(space, fd):
    try:
        termios.tcdrain(fd)
    except termios.error, e:
        e.errno = e.args[0]
        raise convert_error(space, e)
tcdrain.unwrap_spec = [ObjSpace, int]

def tcflush(space, fd, queue):
    try:
        termios.tcflush(fd, queue)
    except termios.error, e:
        e.errno = e.args[0]
        raise convert_error(space, e)
tcflush.unwrap_spec = [ObjSpace, int, int]

def tcflow(space, fd, action):
    try:
        termios.tcflow(fd, action)
    except termios.error, e:
        e.errno = e.args[0]
        raise convert_error(space, e)
tcflow.unwrap_spec = [ObjSpace, int, int]
