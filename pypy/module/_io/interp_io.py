from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.typedef import (
    TypeDef, interp_attrproperty, generic_new_descr)
from pypy.interpreter.gateway import interp2app, Arguments, unwrap_spec
from pypy.module.exceptions.interp_exceptions import W_IOError
from pypy.module._io.interp_iobase import W_IOBase

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
    __new__ = generic_new_descr(W_BytesIO),
    )

class W_BufferedReader(W_BufferedIOBase):
    pass
W_BufferedReader.typedef = TypeDef(
    'BufferedReader', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedReader),
    )

class W_BufferedWriter(W_BufferedIOBase):
    pass
W_BufferedWriter.typedef = TypeDef(
    'BufferedWriter', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedWriter),
    )

class W_BufferedRWPair(W_BufferedIOBase):
    pass
W_BufferedRWPair.typedef = TypeDef(
    'BufferedRWPair', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedRWPair),
    )

class W_BufferedRandom(W_BufferedIOBase):
    pass
W_BufferedRandom.typedef = TypeDef(
    'BufferedRandom', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedRandom),
    )

class W_TextIOWrapper(W_TextIOBase):
    pass
W_TextIOWrapper.typedef = TypeDef(
    'TextIOWrapper', W_TextIOBase.typedef,
    __new__ = generic_new_descr(W_TextIOWrapper),
    )

@unwrap_spec(ObjSpace, Arguments)
def open(space, __args__):
    # XXX cheat!
    w_pyio = space.call_method(space.builtin, '__import__',
                             space.wrap("_pyio"))
    w_func = space.getattr(w_pyio, space.wrap("open"))
    return space.call_args(w_func, __args__)

