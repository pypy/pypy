from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_SliceType(W_TypeObject):

    typename = 'slice'
