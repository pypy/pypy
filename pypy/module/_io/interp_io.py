from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.gateway import interp2app, Arguments
from pypy.module.exceptions.interp_exceptions import W_IOError

DEFAULT_BUFFER_SIZE = 8192

def GenericNew(W_Type):
    def descr_new(space, w_subtype, __args__):
        self = space.allocate_instance(W_Type, w_subtype)
        W_Type.__init__(self, space)
        return space.wrap(self)
    descr_new.unwrap_spec = [ObjSpace, W_Root, Arguments]
    return interp2app(descr_new)

class W_BlockingIOError(W_IOError):
    def __init__(self, space):
        W_IOError.__init__(self, space)
        self.written = 0

    def descr_init(self, space, w_errno, w_strerror, written=0):
        W_IOError.descr_init(self, space, [w_errno, w_strerror])
        self.written = written
    descr_init.unwrap_spec = ['self', ObjSpace, W_Root, W_Root, int]

W_BlockingIOError.typedef = TypeDef(
    'BlockingIOError',
    __doc__ = ("Exception raised when I/O would block "
               "on a non-blocking I/O stream"),
    __new__  = GenericNew(W_BlockingIOError),
    __init__ = interp2app(W_BlockingIOError.descr_init),
    characters_written = interp_attrproperty('written', W_BlockingIOError),
    )

class W_IOBase(Wrappable):
    def __init__(self, space):
        pass

W_IOBase.typedef = TypeDef(
    '_IOBase',
    __new__ = GenericNew(W_IOBase),
    )

class W_RawIOBase(W_IOBase):
    pass
W_RawIOBase.typedef = TypeDef(
    '_RawIOBase', W_IOBase.typedef,
    __new__ = GenericNew(W_RawIOBase),
    )

class W_BufferedIOBase(W_IOBase):
    pass

W_BufferedIOBase.typedef = TypeDef(
    '_BufferedIOBase', W_IOBase.typedef,
    __new__ = GenericNew(W_BufferedIOBase),
    )

class W_TextIOBase(W_IOBase):
    pass
W_TextIOBase.typedef = TypeDef(
    '_TextIOBase', W_IOBase.typedef,
    __new__ = GenericNew(W_TextIOBase),
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
