from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError

from pypy.module.oracle.interp_error import get

class W_ExternalLob(Wrappable):
    def __init__(self, var, pos):
        self.lobVar = var
        self.pos = pos
        self.internalFetchNum = var.internalFetchNum

    def _verify(self, space):
        if self.internalFetchNum != self.lobVar.internalFetchNum:
            raise OperationError(
                get(space).w_ProgrammingError,
                space.wrap(
                    "LOB variable no longer valid after subsequent fetch"))

    def read(self, space, offset=-1, amount=-1):
        self._verify(space)
        return self.lobVar.read(space, self.pos, offset, amount)
    read.unwrap_spec = ['self', ObjSpace, int, int]

    def size(self, space):
        self._verify(space)
        return space.wrap(self.lobVar.getLength(space, self.pos))
    size.unwrap_spec = ['self', ObjSpace]

    def trim(self, space, newSize=0):
        self._verify(space)
        self.lobVar.trim(space, self.pos, newSize)
    trim.unwrap_spec = ['self', ObjSpace, int]

    def desc_str(self, space):
        return self.read(space, offset=1, amount=-1)
    desc_str.unwrap_spec = ['self', ObjSpace]

W_ExternalLob.typedef = TypeDef(
    'ExternalLob',
    read = interp2app(W_ExternalLob.read),
    size = interp2app(W_ExternalLob.size),
    trim = interp2app(W_ExternalLob.trim),
    __str__ = interp2app(W_ExternalLob.desc_str),
    )
