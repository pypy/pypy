from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import operationerrfmt, OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.objspace.std.floattype import float_typedef
from pypy.objspace.std.stringtype import str_typedef
from pypy.objspace.std.unicodetype import unicode_typedef, unicode_from_object
from pypy.objspace.std.inttype import int_typedef
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.tool.sourcetools import func_with_new_name

MIXIN_32 = (int_typedef,) if LONG_BIT == 32 else ()
MIXIN_64 = (int_typedef,) if LONG_BIT == 64 else ()

def new_dtype_getter(name):
    def _get_dtype(space):
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache
        return getattr(get_dtype_cache(space), "w_%sdtype" % name)
    def new(space, w_subtype, w_value):
        dtype = _get_dtype(space)
        return dtype.itemtype.coerce_subtype(space, w_subtype, w_value)
    return func_with_new_name(new, name + "_box_new"), staticmethod(_get_dtype)

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

    def get_dtype(self, space):
        return self._get_dtype(space)

    def descr_str(self, space):
        return space.wrap(self.get_dtype(space).itemtype.str_format(self))

    def descr_format(self, space, w_spec):
        return space.format(self.item(space), w_spec)

    def descr_int(self, space):
        box = self.convert_to(W_LongBox._get_dtype(space))
        assert isinstance(box, W_LongBox)
        return space.wrap(box.value)

    def descr_float(self, space):
        box = self.convert_to(W_Float64Box._get_dtype(space))
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
    descr_truediv = _binop_impl("true_divide")
    descr_mod = _binop_impl("mod")
    descr_pow = _binop_impl("power")
    descr_lshift = _binop_impl("left_shift")
    descr_rshift = _binop_impl("right_shift")
    descr_and = _binop_impl("bitwise_and")
    descr_or = _binop_impl("bitwise_or")
    descr_xor = _binop_impl("bitwise_xor")

    descr_eq = _binop_impl("equal")
    descr_ne = _binop_impl("not_equal")
    descr_lt = _binop_impl("less")
    descr_le = _binop_impl("less_equal")
    descr_gt = _binop_impl("greater")
    descr_ge = _binop_impl("greater_equal")

    descr_radd = _binop_right_impl("add")
    descr_rsub = _binop_right_impl("subtract")
    descr_rmul = _binop_right_impl("multiply")
    descr_rdiv = _binop_right_impl("divide")
    descr_rtruediv = _binop_right_impl("true_divide")
    descr_rmod = _binop_right_impl("mod")
    descr_rpow = _binop_right_impl("power")
    descr_rlshift = _binop_right_impl("left_shift")
    descr_rrshift = _binop_right_impl("right_shift")
    descr_rand = _binop_right_impl("bitwise_and")
    descr_ror = _binop_right_impl("bitwise_or")
    descr_rxor = _binop_right_impl("bitwise_xor")

    descr_pos = _unaryop_impl("positive")
    descr_neg = _unaryop_impl("negative")
    descr_abs = _unaryop_impl("absolute")
    descr_invert = _unaryop_impl("invert")

    def descr_divmod(self, space, w_other):
        w_quotient = self.descr_div(space, w_other)
        w_remainder = self.descr_mod(space, w_other)
        return space.newtuple([w_quotient, w_remainder])

    def descr_rdivmod(self, space, w_other):
        w_quotient = self.descr_rdiv(space, w_other)
        w_remainder = self.descr_rmod(space, w_other)
        return space.newtuple([w_quotient, w_remainder])

    def item(self, space):
        return self.get_dtype(space).itemtype.to_builtin_type(space, self)


class W_BoolBox(W_GenericBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("bool")

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
    descr__new__, _get_dtype = new_dtype_getter("int8")

class W_UInt8Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("uint8")

class W_Int16Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("int16")

class W_UInt16Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("uint16")

class W_Int32Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("int32")

class W_UInt32Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("uint32")

class W_LongBox(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("long")

class W_ULongBox(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("ulong")

class W_Int64Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("int64")

class W_LongLongBox(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter('longlong')

class W_UInt64Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("uint64")

class W_ULongLongBox(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter('ulonglong')

class W_InexactBox(W_NumberBox):
    _attrs_ = ()

class W_FloatingBox(W_InexactBox):
    _attrs_ = ()

class W_Float32Box(W_FloatingBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("float32")

class W_Float64Box(W_FloatingBox, PrimitiveBox):
    descr__new__, _get_dtype = new_dtype_getter("float64")


class W_FlexibleBox(W_GenericBox):
    def __init__(self, arr, ofs, dtype):
        self.arr = arr # we have to keep array alive
        self.ofs = ofs
        self.dtype = dtype

    def get_dtype(self, space):
        return self.arr.dtype

@unwrap_spec(self=W_GenericBox)
def descr_index(space, self):
    return space.index(self.item(space))

class W_VoidBox(W_FlexibleBox):
    @unwrap_spec(item=str)
    def descr_getitem(self, space, item):
        try:
            ofs, dtype = self.dtype.fields[item]
        except KeyError:
            raise OperationError(space.w_IndexError,
                                 space.wrap("Field %s does not exist" % item))
        return dtype.itemtype.read(self.arr, 1, self.ofs, ofs, dtype)

    @unwrap_spec(item=str)
    def descr_setitem(self, space, item, w_value):
        try:
            ofs, dtype = self.dtype.fields[item]
        except KeyError:
            raise OperationError(space.w_IndexError,
                                 space.wrap("Field %s does not exist" % item))
        dtype.itemtype.store(self.arr, 1, self.ofs, ofs,
                             dtype.coerce(space, w_value))

class W_CharacterBox(W_FlexibleBox):
    pass

class W_StringBox(W_CharacterBox):
    def descr__new__string_box(space, w_subtype, w_arg):
        from pypy.module.micronumpy.interp_numarray import W_NDimArray
        from pypy.module.micronumpy.interp_dtype import new_string_dtype

        arg = space.str_w(space.str(w_arg))
        arr = W_NDimArray([1], new_string_dtype(space, len(arg)))
        for i in range(len(arg)):
            arr.storage[i] = arg[i]
        return W_StringBox(arr, 0, arr.dtype)


class W_UnicodeBox(W_CharacterBox):
    def descr__new__unicode_box(space, w_subtype, w_arg):
        from pypy.module.micronumpy.interp_numarray import W_NDimArray
        from pypy.module.micronumpy.interp_dtype import new_unicode_dtype

        arg = space.unicode_w(unicode_from_object(space, w_arg))
        arr = W_NDimArray([1], new_unicode_dtype(space, len(arg)))
        # XXX not this way, we need store
        #for i in range(len(arg)):
        #    arr.storage[i] = arg[i]
        return W_UnicodeBox(arr, 0, arr.dtype)

W_GenericBox.typedef = TypeDef("generic",
    __module__ = "numpypy",

    __new__ = interp2app(W_GenericBox.descr__new__.im_func),

    __str__ = interp2app(W_GenericBox.descr_str),
    __repr__ = interp2app(W_GenericBox.descr_str),
    __format__ = interp2app(W_GenericBox.descr_format),
    __int__ = interp2app(W_GenericBox.descr_int),
    __float__ = interp2app(W_GenericBox.descr_float),
    __nonzero__ = interp2app(W_GenericBox.descr_nonzero),

    __add__ = interp2app(W_GenericBox.descr_add),
    __sub__ = interp2app(W_GenericBox.descr_sub),
    __mul__ = interp2app(W_GenericBox.descr_mul),
    __div__ = interp2app(W_GenericBox.descr_div),
    __truediv__ = interp2app(W_GenericBox.descr_truediv),
    __mod__ = interp2app(W_GenericBox.descr_mod),
    __divmod__ = interp2app(W_GenericBox.descr_divmod),
    __pow__ = interp2app(W_GenericBox.descr_pow),
    __lshift__ = interp2app(W_GenericBox.descr_lshift),
    __rshift__ = interp2app(W_GenericBox.descr_rshift),
    __and__ = interp2app(W_GenericBox.descr_and),
    __or__ = interp2app(W_GenericBox.descr_or),
    __xor__ = interp2app(W_GenericBox.descr_xor),

    __radd__ = interp2app(W_GenericBox.descr_radd),
    __rsub__ = interp2app(W_GenericBox.descr_rsub),
    __rmul__ = interp2app(W_GenericBox.descr_rmul),
    __rdiv__ = interp2app(W_GenericBox.descr_rdiv),
    __rtruediv__ = interp2app(W_GenericBox.descr_rtruediv),
    __rmod__ = interp2app(W_GenericBox.descr_rmod),
    __rdivmod__ = interp2app(W_GenericBox.descr_rdivmod),
    __rpow__ = interp2app(W_GenericBox.descr_rpow),
    __rlshift__ = interp2app(W_GenericBox.descr_rlshift),
    __rrshift__ = interp2app(W_GenericBox.descr_rrshift),
    __rand__ = interp2app(W_GenericBox.descr_rand),
    __ror__ = interp2app(W_GenericBox.descr_ror),
    __rxor__ = interp2app(W_GenericBox.descr_rxor),

    __eq__ = interp2app(W_GenericBox.descr_eq),
    __ne__ = interp2app(W_GenericBox.descr_ne),
    __lt__ = interp2app(W_GenericBox.descr_lt),
    __le__ = interp2app(W_GenericBox.descr_le),
    __gt__ = interp2app(W_GenericBox.descr_gt),
    __ge__ = interp2app(W_GenericBox.descr_ge),

    __pos__ = interp2app(W_GenericBox.descr_pos),
    __neg__ = interp2app(W_GenericBox.descr_neg),
    __abs__ = interp2app(W_GenericBox.descr_abs),
    __invert__ = interp2app(W_GenericBox.descr_invert),

    tolist = interp2app(W_GenericBox.item),
)

W_BoolBox.typedef = TypeDef("bool_", W_GenericBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_BoolBox.descr__new__.im_func),

    __index__ = interp2app(descr_index),
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
    __index__ = interp2app(descr_index),
)

W_UInt8Box.typedef = TypeDef("uint8", W_UnsignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_UInt8Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
)

W_Int16Box.typedef = TypeDef("int16", W_SignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_Int16Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
)

W_UInt16Box.typedef = TypeDef("uint16", W_UnsignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_UInt16Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
)

W_Int32Box.typedef = TypeDef("int32", (W_SignedIntegerBox.typedef,) + MIXIN_32,
    __module__ = "numpypy",
    __new__ = interp2app(W_Int32Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
)

W_UInt32Box.typedef = TypeDef("uint32", W_UnsignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_UInt32Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
)

W_Int64Box.typedef = TypeDef("int64", (W_SignedIntegerBox.typedef,) + MIXIN_64,
    __module__ = "numpypy",
    __new__ = interp2app(W_Int64Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
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
    __index__ = interp2app(descr_index),
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
    __getitem__ = interp2app(W_VoidBox.descr_getitem),
    __setitem__ = interp2app(W_VoidBox.descr_setitem),
)

W_CharacterBox.typedef = TypeDef("character", W_FlexibleBox.typedef,
    __module__ = "numpypy",
)

W_StringBox.typedef = TypeDef("string_", (str_typedef, W_CharacterBox.typedef),
    __module__ = "numpypy",
    __new__ = interp2app(W_StringBox.descr__new__string_box.im_func),
)

W_UnicodeBox.typedef = TypeDef("unicode_", (unicode_typedef, W_CharacterBox.typedef),
    __module__ = "numpypy",
    __new__ = interp2app(W_UnicodeBox.descr__new__unicode_box.im_func),
)
                                          
