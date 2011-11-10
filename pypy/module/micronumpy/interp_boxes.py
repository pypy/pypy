from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.objspace.std.inttype import int_typedef
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.tool.sourcetools import func_with_new_name


MIXIN_64 = (int_typedef,) if LONG_BIT == 64 else ()

def dtype_getter(name):
    @staticmethod
    def get_dtype(space):
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache
        return getattr(get_dtype_cache(space), "w_%sdtype" % name)
    return get_dtype

class W_GenericBox(Wrappable):
    def descr_repr(self, space):
        return space.wrap(self.get_dtype(space).itemtype.str_format(self))

    def descr_int(self, space):
        return space.wrap(self.convert_to(W_LongBox.get_dtype(space)).value)

    def descr_float(self, space):
        return space.wrap(self.convert_to(W_Float64Box.get_dtype(space)).value)

    def _binop_impl(ufunc_name):
        def impl(self, space, w_other):
            from pypy.module.micronumpy import interp_ufuncs
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space, [self, w_other])
        return func_with_new_name(impl, "binop_%s_impl" % ufunc_name)

    descr_div = _binop_impl("divide")

    descr_eq = _binop_impl("equal")


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

class W_UnsignedIntgerBox(W_IntegerBox):
    pass

class W_Int8Box(W_SignedIntegerBox):
    pass

class W_UInt8Box(W_UnsignedIntgerBox):
    pass

class W_Int16Box(W_SignedIntegerBox):
    pass

class W_UInt16Box(W_UnsignedIntgerBox):
    pass

class W_Int32Box(W_SignedIntegerBox):
    pass

class W_UInt32Box(W_UnsignedIntgerBox):
    pass

class W_LongBox(W_SignedIntegerBox):
    get_dtype = dtype_getter("long")

class W_ULongBox(W_UnsignedIntgerBox):
    pass

class W_Int64Box(W_SignedIntegerBox):
    get_dtype = dtype_getter("int64")

class W_UInt64Box(W_UnsignedIntgerBox):
    pass

class W_InexactBox(W_NumberBox):
    pass

class W_FloatingBox(W_InexactBox):
    pass

class W_Float32Box(W_FloatingBox):
    pass

class W_Float64Box(W_FloatingBox):
    get_dtype = dtype_getter("float64")



W_GenericBox.typedef = TypeDef("generic",
    __module__ = "numpy",

    __repr__ = interp2app(W_GenericBox.descr_repr),
    __int__ = interp2app(W_GenericBox.descr_int),
    __float__ = interp2app(W_GenericBox.descr_float),

    __div__ = interp2app(W_GenericBox.descr_div),
    __eq__ = interp2app(W_GenericBox.descr_eq),

)

W_BoolBox.typedef = TypeDef("bool_", W_GenericBox.typedef,
    __module__ = "numpy",
)

W_NumberBox.typedef = TypeDef("number", W_GenericBox.typedef,
    __module__ = "numpy",
)

W_IntegerBox.typedef = TypeDef("integer", W_NumberBox.typedef,
    __module__ = "numpy",
)

W_SignedIntegerBox.typedef = TypeDef("signedinteger", W_IntegerBox.typedef,
    __module__ = "numpy",
)

if LONG_BIT == 32:
    long_name = "int32"
elif LONG_BIT == 64:
    long_name = "int64"
W_LongBox.typedef = TypeDef(long_name, (W_SignedIntegerBox.typedef, int_typedef,),
    __module__ = "numpy",
)

W_Int64Box.typedef = TypeDef("int64", (W_SignedIntegerBox.typedef,) + MIXIN_64,
    __module__ = "numpy",
)