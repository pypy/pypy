from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_IntType(W_TypeObject):

    typename = 'int'
