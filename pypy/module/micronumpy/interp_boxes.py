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

class PrimitiveBox(object):
    _mixin_ = True

    def __init__(self, value):
        self.value = value

    def convert_to(self, dtype):
        return dtype.box(self.value)

class W_GenericBox(Wrappable):
    _attrs_ = ()

    def descr_repr(self, space):
        return space.wrap(self.get_dtype(space).itemtype.str_format(self))

    def descr_int(self, space):
        box = self.convert_to(W_LongBox.get_dtype(space))
        assert isinstance(box, W_LongBox)
        return space.wrap(box.value)

    def descr_float(self, space):
        box = self.convert_to(W_Float64Box.get_dtype(space))
        assert isinstance(box, W_Float64Box)
        return space.wrap(box.value)

    def _binop_impl(ufunc_name):
        def impl(self, space, w_other):
            from pypy.module.micronumpy import interp_ufuncs
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space, [self, w_other])
        return func_with_new_name(impl, "binop_%s_impl" % ufunc_name)

    def _binop_right_impl(ufunc_name):
        def impl(self, space, w_other):
            from pypy.module.micronumpy import interp_ufuncs
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space, [w_other, self])
        return func_with_new_name(impl, "binop_right_%s_impl" % ufunc_name)

    def _unaryop_impl(ufunc_name):
        def impl(self, space):
            from pypy.module.micronumpy import interp_ufuncs
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space, [self])
        return func_with_new_name(impl, "unaryop_%s_impl" % ufunc_name)

    descr_add = _binop_impl("add")
    descr_sub = _binop_impl("subtract")
    descr_mul = _binop_impl("multiply")
    descr_div = _binop_impl("divide")
    descr_eq = _binop_impl("equal")
    descr_lt = _binop_impl("less")

    descr_rmul = _binop_right_impl("multiply")

    descr_neg = _unaryop_impl("negative")
    descr_abs = _unaryop_impl("absolute")


class W_BoolBox(W_GenericBox, PrimitiveBox):
    pass

class W_NumberBox(W_GenericBox):
    _attrs_ = ()

class W_IntegerBox(W_NumberBox):
    pass

class W_SignedIntegerBox(W_IntegerBox):
    pass

class W_UnsignedIntgerBox(W_IntegerBox):
    pass

class W_Int8Box(W_SignedIntegerBox, PrimitiveBox):
    pass

class W_UInt8Box(W_UnsignedIntgerBox, PrimitiveBox):
    pass

class W_Int16Box(W_SignedIntegerBox, PrimitiveBox):
    pass

class W_UInt16Box(W_UnsignedIntgerBox, PrimitiveBox):
    pass

class W_Int32Box(W_SignedIntegerBox, PrimitiveBox):
    pass

class W_UInt32Box(W_UnsignedIntgerBox, PrimitiveBox):
    pass

class W_LongBox(W_SignedIntegerBox, PrimitiveBox):
    get_dtype = dtype_getter("long")

class W_ULongBox(W_UnsignedIntgerBox, PrimitiveBox):
    pass

class W_Int64Box(W_SignedIntegerBox, PrimitiveBox):
    get_dtype = dtype_getter("int64")

class W_UInt64Box(W_UnsignedIntgerBox, PrimitiveBox):
    pass

class W_InexactBox(W_NumberBox):
    _attrs_ = ()

class W_FloatingBox(W_InexactBox):
    _attrs_ = ()

class W_Float32Box(W_FloatingBox, PrimitiveBox):
    get_dtype = dtype_getter("float32")

class W_Float64Box(W_FloatingBox, PrimitiveBox):
    get_dtype = dtype_getter("float64")



W_GenericBox.typedef = TypeDef("generic",
    __module__ = "numpy",

    __repr__ = interp2app(W_GenericBox.descr_repr),
    __int__ = interp2app(W_GenericBox.descr_int),
    __float__ = interp2app(W_GenericBox.descr_float),

    __add__ = interp2app(W_GenericBox.descr_add),
    __sub__ = interp2app(W_GenericBox.descr_sub),
    __mul__ = interp2app(W_GenericBox.descr_mul),
    __div__ = interp2app(W_GenericBox.descr_div),

    __rmul__ = interp2app(W_GenericBox.descr_rmul),

    __eq__ = interp2app(W_GenericBox.descr_eq),
    __lt__ = interp2app(W_GenericBox.descr_lt),

    __neg__ = interp2app(W_GenericBox.descr_neg),
    __abs__ = interp2app(W_GenericBox.descr_abs),
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