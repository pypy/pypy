from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_BoolType(W_TypeObject):

    typename = 'bool'
