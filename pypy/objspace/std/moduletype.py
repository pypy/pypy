from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_ModuleType(W_TypeObject):

    typename = 'module'
