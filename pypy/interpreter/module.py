"""
Module objects.
"""

from pypy.interpreter.baseobjspace import Wrappable

class Module(Wrappable):
    """A module."""

    def __init__(self, space, w_name, w_dict=None):
        self.space = space
        if w_dict is None:
            w_dict = space.newdict([])
        self.w_dict = w_dict
        self.w_name = w_name
        space.setitem(w_dict, space.wrap('__name__'), w_name)
