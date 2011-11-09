from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef


class W_GenericBox(Wrappable):
    pass

class W_BoolBox(Wrappable):
    def __init__(self, value):
        self.value = value

class W_NumberBox(W_GenericBox):
    def __init__(self, value):
        self.value = value

    def convert_to(self, dtype):
        return dtype.box(self.value)

class W_IntegerBox(W_NumberBox):
    pass

class W_SignedIntegerBox(W_IntegerBox):
    pass

class W_Int64Box(W_SignedIntegerBox):
    pass

class W_InexactBox(W_NumberBox):
    pass

class W_FloatingBox(W_InexactBox):
    pass

class W_Float64Box(W_FloatingBox):
    def descr_get_dtype(self, space):
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache
        return get_dtype_cache(space).w_float64dtype

W_GenericBox.typedef = TypeDef("generic",
    __module__ = "numpy",
)

W_BoolBox.typedef = TypeDef("bool_", W_GenericBox.typedef,
    __module__ = "numpy",
)