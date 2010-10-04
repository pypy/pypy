from pypy.interpreter.baseobjspace import ObjSpace, Wrappable
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.module.exceptions.interp_exceptions import W_IOError

DEFAULT_BUFFER_SIZE = 8192


class W_BlockingIOError(W_IOError):
    def __init__(self, space):
        W_IOError.__init__(self, space)
        self.written = 0

    def descr_init(self, space, w_errno, w_strerror, written=0):
        W_IOError.descr_init(self, space, [w_errno, w_strerror])
        self.written = written

W_BlockingIOError.typedef = TypeDef(
    'BlockingIOError',
    __doc__ = ("Exception raised when I/O would block "
               "on a non-blocking I/O stream"),
    characters_written = interp_attrproperty('written', W_BlockingIOError),
    )

class W_IOBase(Wrappable):
    pass
W_IOBase.typedef = TypeDef(
    '_IOBase',
    )

class W_RawIOBase(W_IOBase):
    pass
W_RawIOBase.typedef = TypeDef(
    '_RawIOBase', W_IOBase.typedef,
    )

class W_BufferedIOBase(W_IOBase):
    pass
W_BufferedIOBase.typedef = TypeDef(
    '_BufferedIOBase', W_IOBase.typedef,
    )

class W_TextIOBase(W_IOBase):
    pass
W_TextIOBase.typedef = TypeDef(
    '_TextIOBase', W_IOBase.typedef,
    )

class W_FileIO(W_RawIOBase):
    pass
W_FileIO.typedef = TypeDef(
    'FileIO', W_RawIOBase.typedef,
    )

class W_BytesIO(W_BufferedIOBase):
    pass
W_BytesIO.typedef = TypeDef(
    'BytesIO', W_BufferedIOBase.typedef,
    )

class W_StringIO(W_TextIOBase):
    pass
W_StringIO.typedef = TypeDef(
    'StringIO', W_TextIOBase.typedef,
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
