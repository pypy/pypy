
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.rlib import jit

class W_FlatIterator(Wrappable):
    def __init__(self, arr):
        self.arr = arr
        self.iter = self.arr.create_iter()
        self.index = 0

    def descr_next(self, space):
        if self.iter.done():
            raise OperationError(space.w_StopIteration, space.w_None)
        w_res = self.iter.getitem()
        self.iter.next()
        self.index += 1
        return w_res

    def descr_iter(self):
        return self

W_FlatIterator.typedef = TypeDef(
    'flatiter',
    __iter__ = interp2app(W_FlatIterator.descr_iter),    

    next = interp2app(W_FlatIterator.descr_next),
)
