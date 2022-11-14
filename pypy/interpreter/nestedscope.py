from rpython.tool.uid import uid
from rpython.rlib import jit

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt
from pypy.interpreter.mixedmodule import MixedModule


def make_cell_cmp(op):
    import operator
    cmp = getattr(operator, op)
    def descr_cell_(self, space, w_other):
        if not isinstance(w_other, Cell):
            return space.w_NotImplemented
        if self.w_value is None or w_other.w_value is None:
            return space.newbool(cmp(self._cmp_one_empty(w_other), 0))
        return getattr(space, op)(self.w_value, w_other.w_value)
    descr_cell_.func_name += op
    return descr_cell_


class Cell(W_Root):
    "A simple container for a wrapped value."

    _immutable_fields_ = ['family']

    def __init__(self, w_value, family):
        self.w_value = w_value
        self.family = family

    def get(self):
        if jit.isconstant(self):
            # ever_mutated is False if we never see a transition from not-None to
            # not-None. That means _elidable_get might return an out-of-date
            # None, and by now the cell was written to, with a not-None. So if
            # we see a None, we don't return that and instead read self.w_value
            # in the code below.
            if not self.family.ever_mutated:
                w_res = self._elidable_get()
                if w_res is not None:
                    return w_res
        if self.w_value is None:
            raise ValueError("get() from an empty cell")
        return self.w_value

    def empty(self):
        return self.w_value is None

    @jit.elidable
    def _elidable_get(self):
        return self.w_value

    def set(self, w_value):
        if not self.family.ever_mutated and self.w_value is not None:
            self.family.ever_mutated = True
        self.w_value = w_value

    def delete(self):
        if not self.family.ever_mutated:
            self.family.ever_mutated = True
        if self.w_value is None:
            raise ValueError("delete() on an empty cell")
        self.w_value = None

    def _cmp_one_empty(self, w_other):
        if self.w_value is None:
            if w_other.w_value is None:
                return 0
            return -1
        else:
            assert w_other.w_value is None
            return 1

    descr_eq = make_cell_cmp("eq")
    descr_ne = make_cell_cmp("ne")
    descr_lt = make_cell_cmp("lt")
    descr_gt = make_cell_cmp("gt")
    descr_ge = make_cell_cmp("ge")
    descr_le = make_cell_cmp("le")

    def descr__reduce__(self, space):
        w_mod = space.getbuiltinmodule('_pickle_support')
        mod = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('cell_new')
        if self.w_value is None:    # when would this happen?
            return space.newtuple2(new_inst, space.newtuple([]))
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

    def descr_set_cell_contents(self, space, w_value):
        return self.set(w_value)

    def descr_del_cell_contents(self, space):
        try:
            return self.delete()
        except ValueError:
            pass # CPython ignores it


def descr_new_cell(space, w_type, w_obj=None):
    """ Create and return a new cell. If an argument is given, it is used as
    the cell_contents of the cell, otherwise the cell is empty. """
    return Cell(w_obj, DUMMY_FAMILY)


class CellFamily(object):
    _immutable_fields_ = ['ever_mutated?']

    def __init__(self, name):
        self.name = name
        self.ever_mutated = False

DUMMY_FAMILY = CellFamily("<dummy>")
DUMMY_FAMILY.ever_mutated = True
