from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_FloatType(W_TypeObject):

    typename = 'float'
