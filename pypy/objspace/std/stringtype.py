from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_StringType(W_TypeObject):

    typename = 'str'

    str_join  = MultiMethod('join', 2)
    str_split = MultiMethod('split', 2)
