from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject
from inttype import W_IntType


class W_BoolType(W_TypeObject):

    typename = 'bool'
    staticbases = (W_IntType,)
