from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.typedef import (
    TypeDef, interp_attrproperty, generic_new_descr)
from pypy.interpreter.gateway import interp2app, Arguments, unwrap_spec
from pypy.module.exceptions.interp_exceptions import W_IOError
from pypy.module._io.interp_iobase import W_IOBase

class W_BlockingIOError(W_IOError):
    def __init__(self, space):
        W_IOError.__init__(self, space)
        self.written = 0

    @unwrap_spec('self', ObjSpace, W_Root, W_Root, int)
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

@unwrap_spec(ObjSpace, Arguments)
def open(space, __args__):
    # XXX cheat!
    w_pyio = space.call_method(space.builtin, '__import__',
                             space.wrap("_pyio"))
    w_func = space.getattr(w_pyio, space.wrap("open"))
    return space.call_args(w_func, __args__)

