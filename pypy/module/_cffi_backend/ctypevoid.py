"""
Void.
"""

from pypy.module._cffi_backend.ctypeobj import W_CType


class W_CTypeVoid(W_CType):
    cast_anything = True

    def __init__(self, space):
        W_CType.__init__(self, space, -1, "void", len("void"))
