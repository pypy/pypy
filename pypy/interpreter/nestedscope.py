from rpython.tool.uid import uid

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt
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

    def descr__lt__(self, space, w_other):
        if not isinstance(w_other, Cell):
            return space.w_NotImplemented
        if self.w_value is None:
            # an empty cell is alway less than a non-empty one
            if w_other.w_value is None:
                return space.w_False
            return space.w_True
        elif w_other.w_value is None:
            return space.w_False
        return space.lt(self.w_value, w_other.w_value)

    def descr__eq__(self, space, w_other):
        if not isinstance(w_other, Cell):
            return space.w_NotImplemented
        if self.w_value is None or w_other.w_value is None:
            return space.wrap(self.w_value == w_other.w_value)
        return space.eq(self.w_value, w_other.w_value)

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
        self.w_value = space.getitem(w_state, space.newint(0))

    def __repr__(self):
        """ representation for debugging purposes """
        if self.w_value is None:
            content = ""
        else:
            content = repr(self.w_value)
        return "<%s(%s) at 0x%x>" % (self.__class__.__name__,
                                     content, uid(self))

    def descr__repr__(self, space):
        if self.w_value is None:
            content = "empty"
        else:
            content = "%s object at 0x%s" % (space.type(self.w_value).name,
                                             self.w_value.getaddrstring(space))
        s = "<cell at 0x%s: %s>" % (self.getaddrstring(space), content)
        return space.newtext(s)

    def descr__cell_contents(self, space):
        try:
            return self.get()
        except ValueError:
            raise oefmt(space.w_ValueError, "Cell is empty")
