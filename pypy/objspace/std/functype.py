from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_FuncType(W_TypeObject):

    typename = 'FunctionType'
