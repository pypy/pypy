from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_NoneType(W_TypeObject):

    typename = 'NoneType'

registerimplementation(W_NoneType)
