from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_NullType(W_TypeObject):

    typename = 'NullType'
