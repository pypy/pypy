from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_InstMethType(W_TypeObject):

    typename = 'MethodType'
