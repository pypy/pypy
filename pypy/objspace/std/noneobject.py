"""
  None Object implementation

  ok and tested
""" 

from pypy.objspace.std.objspace import *

class W_NoneObject(W_Object):
    from pypy.objspace.std.nonetype import none_typedef as typedef

    def unwrap(w_self, space):
        return None

registerimplementation(W_NoneObject)

W_NoneObject.w_None = W_NoneObject()

def nonzero__None(space, w_none):
    return space.w_False

def repr__None(space, w_none):
    return space.wrap('None')

register_all(vars())

