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
        if not space.is_true(space.contains(w_dict, space.wrap('__doc__'))):
            space.setitem(w_dict, space.wrap('__doc__'), space.w_None)

    def getdict(self):
        return self.w_dict

    def setdict(self, w_dict):
        self.w_dict = w_dict

    def descr_module__new__(space, w_subtype, __args__):
        module = space.allocate_instance(Module, w_subtype)
        module.__init__(space, space.wrap('?'))
        return space.wrap(module)

    def descr_module__init__(self, w_name, w_doc=None):
        space = self.space
        self.w_name = w_name
        space.setitem(self.w_dict, space.wrap('__name__'), w_name)
        if w_doc is not None:
            space.setitem(self.w_dict, space.wrap('__doc__'), w_doc)
