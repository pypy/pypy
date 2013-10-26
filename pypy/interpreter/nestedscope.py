from rpython.tool.uid import uid

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError
from pypy.interpreter.mixedmodule import MixedModule


class Cell(W_Root):
    "A simple container for a wrapped value."

    def __init__(self, w_value=None):
        self.w_value = w_value

    def clone(self):
        return self.__class__(self.w_value)

    def empty(self):
        return self.w_value is None

    def get(self):
        if self.w_value is None:
            raise ValueError("get() from an empty cell")
        return self.w_value

    def set(self, w_value):
        self.w_value = w_value

    def delete(self):
        if self.w_value is None:
            raise ValueError("delete() on an empty cell")
        self.w_value = None

    def descr__cmp__(self, space, w_other):
        if not isinstance(w_other, Cell):
            return space.w_NotImplemented

        if self.w_value is None:
            if w_other.w_value is None:
                return space.newint(0)
            return space.newint(-1)
        elif w_other.w_value is None:
            return space.newint(1)

        return space.cmp(self.w_value, w_other.w_value)

    def descr__reduce__(self, space):
        w_mod = space.getbuiltinmodule('_pickle_support')
        mod = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('cell_new')
        if self.w_value is None:    # when would this happen?
            return space.newtuple([new_inst, space.newtuple([])])
        tup = [self.w_value]
        return space.newtuple([new_inst, space.newtuple([]),
                               space.newtuple(tup)])

    def descr__setstate__(self, space, w_state):
        self.w_value = space.getitem(w_state, space.wrap(0))

    def __repr__(self):
        """ representation for debugging purposes """
        if self.w_value is None:
            content = ""
        else:
            content = repr(self.w_value)
        return "<%s(%s) at 0x%x>" % (self.__class__.__name__,
                                     content, uid(self))

    def descr__cell_contents(self, space):
        try:
            return self.get()
        except ValueError:
            raise OperationError(space.w_ValueError, space.wrap("Cell is empty"))
