from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace
from pypy.interpreter.gateway import interp2app

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
    read.unwrap_spec=['self', ObjSpace, int, int]

    def desc_str(self, space):
        return self.read(space, offset=1, amount=-1)
    desc_str.unwrap_spec=['self', ObjSpace]

W_ExternalLob.typedef = TypeDef(
    'ExternalLob',
    read = interp2app(W_ExternalLob.read,
                      unwrap_spec=W_ExternalLob.read.unwrap_spec),
    __str__ = interp2app(W_ExternalLob.desc_str,
                         unwrap_spec=W_ExternalLob.desc_str.unwrap_spec),
    )
