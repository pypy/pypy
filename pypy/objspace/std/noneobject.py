"""
  None Object implementation

  ok and tested
""" 

from pypy.objspace.std.objspace import *

class W_NoneObject(W_Object):
    from pypy.objspace.std.nonetype import none_typedef as typedef
registerimplementation(W_NoneObject)

def unwrap__None(space, w_none):
    return None

def is_true__None(space, w_none):
    return False

def repr__None(space, w_none):
    return space.wrap('None')

register_all(vars())

