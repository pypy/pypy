"""
Reviewed 03-06-22
"""
from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_SeqIterType(W_TypeObject):

    typename = 'SeqIterType'

registerimplementation(W_SeqIterType)
