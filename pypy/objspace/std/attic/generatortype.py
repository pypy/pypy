from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_GeneratorType(W_TypeObject):

    typename = 'GeneratorType'

registerimplementation(W_GeneratorType)
