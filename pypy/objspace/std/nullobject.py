"""
  Null Object implementation

  ok and tested
""" 

from pypy.objspace.std.objspace import *
from nulltype import W_NullType

class W_NullObject(W_Object):
    statictype = W_NullType
registerimplementation(W_NullObject)

def unwrap__Null(space, w_null):
    return Null

def is_true__Null(space, w_null):
    return False

def repr__Null(space, w_null):
    return space.wrap('Null')

register_all(vars())

