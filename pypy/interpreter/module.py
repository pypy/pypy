"""
Module objects.
"""

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError


class Module(Wrappable):
    """A module."""

    def __init__(self, space, w_name):
        self.space = space
        self.w_dict = space.newdict([(space.wrap('__name__'), w_name)])
        self.w_name = w_name

    def pypy_getattr(self, w_attr):
        space = self.space
        if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
            return self.w_dict
        try:
            return space.getitem(self.w_dict, w_attr)
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                raise
            # XXX fix error message
            raise OperationError(space.w_AttributeError, w_attr)

    def pypy_setattr(self, w_attr, w_value):
        self.space.setitem(self.w_dict, w_attr, w_value)
