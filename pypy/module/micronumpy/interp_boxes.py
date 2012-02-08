from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import operationerrfmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.objspace.std.floattype import float_typedef
from pypy.objspace.std.inttype import int_typedef
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.tool.sourcetools import func_with_new_name

MIXIN_32 = (int_typedef,) if LONG_BIT == 32 else ()
MIXIN_64 = (int_typedef,) if LONG_BIT == 64 else ()

def new_dtype_getter(name):
    def get_dtype(space):
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache
        return getattr(get_dtype_cache(space), "w_%sdtype" % name)
    def new(space, w_subtype, w_value):
        dtype = get_dtype(space)
        return dtype.itemtype.coerce_subtype(space, w_subtype, w_value)
    return func_with_new_name(new, name + "_box_new"), staticmethod(get_dtype)

class PrimitiveBox(object):
    _mixin_ = True

    def __init__(self, value):
        self.value = value

    def convert_to(self, dtype):
        return dtype.box(self.value)


class W_GenericBox(Wrappable):
    _attrs_ = ()

    def descr__new__(space, w_subtype, __args__):
        raise operationerrfmt(space.w_TypeError, "cannot create '%s' instances",
            w_subtype.getname(space, '?')
        )

    def descr_str(self, space):
        return self.descr_repr(space)

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

    def descr_nonzero(self, space):
        dtype = self.get_dtype(space)
        return space.wrap(dtype.itemtype.bool(self))

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
    descr_pow = _binop_impl("power")
    descr_eq = _binop_impl("equal")
    descr_ne = _binop_impl("not_equal")
    descr_lt = _binop_impl("less")
    descr_le = _binop_impl("less_equal")
    descr_gt = _binop_impl("greater")
    descr_ge = _binop_impl("greater_equal")

    descr_radd = _binop_right_impl("add")
    descr_rsub = _binop_right_impl("subtract")
    descr_rmul = _binop_right_impl("multiply")

    descr_neg = _unaryop_impl("negative")
    descr_abs = _unaryop_impl("absolute")

    def item(self, space):
        return self.get_dtype(space).itemtype.to_builtin_type(space, self)


class W_BoolBox(W_GenericBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("bool")

class W_NumberBox(W_GenericBox):
    _attrs_ = ()

class W_IntegerBox(W_NumberBox):
    def int_w(self, space):
        return space.int_w(self.descr_int(space))

class W_SignedIntegerBox(W_IntegerBox):
    pass

class W_UnsignedIntegerBox(W_IntegerBox):
    pass

class W_Int8Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("int8")

class W_UInt8Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("uint8")

class W_Int16Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("int16")

class W_UInt16Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("uint16")

class W_Int32Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("int32")

class W_UInt32Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("uint32")

class W_LongBox(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("long")

class W_ULongBox(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("ulong")

class W_Int64Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("int64")

class W_LongLongBox(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter('longlong')

class W_UInt64Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("uint64")

class W_ULongLongBox(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter('ulonglong')

class W_InexactBox(W_NumberBox):
    _attrs_ = ()

class W_FloatingBox(W_InexactBox):
    _attrs_ = ()

class W_Float32Box(W_FloatingBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("float32")

class W_Float64Box(W_FloatingBox, PrimitiveBox):
    descr__new__, get_dtype = new_dtype_getter("float64")


class W_FlexibleBox(W_GenericBox):
    pass

class W_VoidBox(W_FlexibleBox):
    pass


W_GenericBox.typedef = TypeDef("generic",
    __module__ = "numpypy",

    __new__ = interp2app(W_GenericBox.descr__new__.im_func),

    __str__ = interp2app(W_GenericBox.descr_str),
    __repr__ = interp2app(W_GenericBox.descr_repr),
    __int__ = interp2app(W_GenericBox.descr_int),
    __float__ = interp2app(W_GenericBox.descr_float),
    __nonzero__ = interp2app(W_GenericBox.descr_nonzero),

    __add__ = interp2app(W_GenericBox.descr_add),
    __sub__ = interp2app(W_GenericBox.descr_sub),
    __mul__ = interp2app(W_GenericBox.descr_mul),
    __div__ = interp2app(W_GenericBox.descr_div),
    __pow__ = interp2app(W_GenericBox.descr_pow),

    __radd__ = interp2app(W_GenericBox.descr_radd),
    __rsub__ = interp2app(W_GenericBox.descr_rsub),
    __rmul__ = interp2app(W_GenericBox.descr_rmul),

    __eq__ = interp2app(W_GenericBox.descr_eq),
    __ne__ = interp2app(W_GenericBox.descr_ne),
    __lt__ = interp2app(W_GenericBox.descr_lt),
    __le__ = interp2app(W_GenericBox.descr_le),
    __gt__ = interp2app(W_GenericBox.descr_gt),
    __ge__ = interp2app(W_GenericBox.descr_ge),

    __neg__ = interp2app(W_GenericBox.descr_neg),
    __abs__ = interp2app(W_GenericBox.descr_abs),

    tolist = interp2app(W_GenericBox.item),
)

W_BoolBox.typedef = TypeDef("bool_", W_GenericBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_BoolBox.descr__new__.im_func),
)

W_NumberBox.typedef = TypeDef("number", W_GenericBox.typedef,
    __module__ = "numpypy",
)

W_IntegerBox.typedef = TypeDef("integer", W_NumberBox.typedef,
    __module__ = "numpypy",
)

W_SignedIntegerBox.typedef = TypeDef("signedinteger", W_IntegerBox.typedef,
    __module__ = "numpypy",
)

W_UnsignedIntegerBox.typedef = TypeDef("unsignedinteger", W_IntegerBox.typedef,
    __module__ = "numpypy",
)

W_Int8Box.typedef = TypeDef("int8", W_SignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_Int8Box.descr__new__.im_func),
)

W_UInt8Box.typedef = TypeDef("uint8", W_UnsignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_UInt8Box.descr__new__.im_func),
)

W_Int16Box.typedef = TypeDef("int16", W_SignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_Int16Box.descr__new__.im_func),
)

W_UInt16Box.typedef = TypeDef("uint16", W_UnsignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_UInt16Box.descr__new__.im_func),
)

W_Int32Box.typedef = TypeDef("int32", (W_SignedIntegerBox.typedef,) + MIXIN_32,
    __module__ = "numpypy",
    __new__ = interp2app(W_Int32Box.descr__new__.im_func),
)

W_UInt32Box.typedef = TypeDef("uint32", W_UnsignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_UInt32Box.descr__new__.im_func),
)

W_Int64Box.typedef = TypeDef("int64", (W_SignedIntegerBox.typedef,) + MIXIN_64,
    __module__ = "numpypy",
    __new__ = interp2app(W_Int64Box.descr__new__.im_func),
)

if LONG_BIT == 32:
    W_LongBox = W_Int32Box
    W_ULongBox = W_UInt32Box
elif LONG_BIT == 64:
    W_LongBox = W_Int64Box
    W_ULongBox = W_UInt64Box

W_UInt64Box.typedef = TypeDef("uint64", W_UnsignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_UInt64Box.descr__new__.im_func),
)

W_InexactBox.typedef = TypeDef("inexact", W_NumberBox.typedef,
    __module__ = "numpypy",
)

W_FloatingBox.typedef = TypeDef("floating", W_InexactBox.typedef,
    __module__ = "numpypy",
)

W_Float32Box.typedef = TypeDef("float32", W_FloatingBox.typedef,
    __module__ = "numpypy",

    __new__ = interp2app(W_Float32Box.descr__new__.im_func),
)

W_Float64Box.typedef = TypeDef("float64", (W_FloatingBox.typedef, float_typedef),
    __module__ = "numpypy",

    __new__ = interp2app(W_Float64Box.descr__new__.im_func),
)


W_FlexibleBox.typedef = TypeDef("flexible", W_GenericBox.typedef,
    __module__ = "numpypy",
)

W_VoidBox.typedef = TypeDef("void", W_FlexibleBox.typedef,
    __module__ = "numpypy",
)
