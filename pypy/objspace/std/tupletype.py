from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_TupleType(W_TypeObject):

    typename = 'tuple'
